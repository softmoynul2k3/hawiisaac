import base64
import os
import re
from typing import List, Optional

import google.genai as genai
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
import io

from app.auth import login_required
from app.config import settings
from applications.ai.schema import (
    EquipmentDetection,
    EquipmentInfo,
    EquipmentInfoRequest,
    EquipmentInfoResponse,
    EquipmentScanRequest,
    EquipmentScanResponse,
)
from applications.user.models import User

router = APIRouter(tags=["AI Equipment Detection"])

# Initialize Gemini API
if not settings.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in settings")

client = genai.Client(api_key=settings.GEMINI_API_KEY)


def _extract_equipment_names(response_text: str) -> List[EquipmentDetection]:
    """Extract equipment names and confidence from AI response"""
    equipment_list = []
    
    # Look for patterns like "Equipment: name (confidence)" or similar
    patterns = [
        r'Equipment:\s*([^(]+)\s*\((\d+(?:\.\d+)?)\)',
        r'(\w+(?:\s+\w+)*)\s*\((\d+(?:\.\d+)?)\)',
        r'-\s*([^(]+)\s*\((\d+(?:\.\d+)?)\)',
        r'(\w+(?:\s+\w+)*)\s*-\s*(\d+(?:\.\d+)?)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        for match in matches:
            name = match[0].strip()
            confidence = float(match[1])
            if confidence > 1.0:
                confidence = confidence / 100.0  # Convert percentage to decimal
            
            if name and confidence > 0.3:  # Filter low confidence detections
                equipment_list.append(EquipmentDetection(
                    name=name,
                    confidence=min(confidence, 1.0),
                    description=None
                ))
    
    # If no structured matches found, try to extract any equipment-related terms
    if not equipment_list:
        equipment_keywords = [
            'dumbbell', 'barbell', 'bench', 'squat', 'deadlift', 'press', 'curl',
            'machine', 'treadmill', 'bike', 'elliptical', 'rower', 'cable',
            'kettlebell', 'medicine ball', 'resistance band', 'pull up', 'dip'
        ]
        
        words = response_text.lower().split()
        for keyword in equipment_keywords:
            if keyword in response_text.lower():
                equipment_list.append(EquipmentDetection(
                    name=keyword.title(),
                    confidence=0.7,
                    description=None
                ))
                break  # Only add one if using fallback
    
    return equipment_list


def _get_primary_equipment(equipment_list: List[EquipmentDetection]) -> Optional[str]:
    """Get the equipment with highest confidence"""
    if not equipment_list:
        return None
    
    primary = max(equipment_list, key=lambda x: x.confidence)
    return primary.name if primary.confidence > 0.5 else None


@router.post("/scan-equipment", response_model=EquipmentScanResponse)
async def scan_equipment_image(
    payload: EquipmentScanRequest,
    current_user: User = Depends(login_required)
):
    """
    Scan an image to identify gym equipment using Gemini AI
    """
    try:
        # Decode base64 image
        image_data = base64.b64decode(payload.image_data)
        image = Image.open(io.BytesIO(image_data))
        
        # Prepare prompt for equipment detection
        default_prompt = """
        Analyze this image and identify any gym equipment visible. 
        For each equipment found, provide the name and confidence level (0-1).
        Focus on common gym equipment like dumbbells, barbells, benches, machines, etc.
        Format your response as a list with equipment names and confidence scores.
        Example format:
        Equipment: Dumbbell (0.95)
        Equipment: Bench Press (0.87)
        """
        
        prompt = payload.prompt or default_prompt
        
        # Generate response from Gemini
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt, image]
        )
        response_text = response.text
        
        # Extract equipment information
        equipment_list = _extract_equipment_names(response_text)
        primary_equipment = _get_primary_equipment(equipment_list)
        
        return EquipmentScanResponse(
            success=True,
            equipment_detected=equipment_list,
            primary_equipment=primary_equipment
        )
        
    except Exception as e:
        return EquipmentScanResponse(
            success=False,
            equipment_detected=[],
            error_message=f"Failed to process image: {str(e)}"
        )


@router.post("/equipment-info", response_model=EquipmentInfoResponse)
async def get_equipment_info(
    payload: EquipmentInfoRequest,
    current_user: User = Depends(login_required)
):
    """
    Get detailed information about a specific piece of equipment
    """
    try:
        prompt = f"""
        Provide detailed information about the gym equipment: {payload.equipment_name}
        Include:
        - Category (e.g., strength training, cardio, etc.)
        - Primary muscle groups worked
        - Brief description
        - 3-5 common exercises performed with this equipment
        
        Format the response clearly with each section labeled.
        """
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        response_text = response.text
        
        # Parse the response (simple text parsing for now)
        category = "Strength Training"  # Default
        muscle_groups = []
        description = response_text.split('\n')[0] if response_text else "Gym equipment"
        common_exercises = []
        
        # Try to extract structured information
        lines = response_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip().lower()
            if 'category' in line:
                category = line.split(':', 1)[-1].strip() if ':' in line else category
            elif 'muscle' in line or 'target' in line:
                if ':' in line:
                    muscles = line.split(':', 1)[-1].strip()
                    muscle_groups = [m.strip() for m in muscles.split(',')]
            elif 'exercise' in line:
                if ':' in line:
                    exercises = line.split(':', 1)[-1].strip()
                    common_exercises = [e.strip() for e in exercises.split(',')]
        
        equipment_info = EquipmentInfo(
            name=payload.equipment_name,
            category=category,
            muscle_groups=muscle_groups,
            description=description,
            common_exercises=common_exercises
        )
        
        return EquipmentInfoResponse(
            success=True,
            equipment=equipment_info
        )
        
    except Exception as e:
        return EquipmentInfoResponse(
            success=False,
            error_message=f"Failed to get equipment info: {str(e)}"
        )


@router.post("/scan-equipment-upload", response_model=EquipmentScanResponse)
async def scan_equipment_image_upload(
    image: UploadFile = File(..., description="Image file to scan for equipment detection")
):
    """
    Scan an uploaded image file to identify gym equipment using Gemini AI
    """
    try:
        # Read uploaded file into memory
        image_bytes = await image.read()
        pil_image = Image.open(io.BytesIO(image_bytes))

        # Generate response from Gemini
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=["""Analyze this image and identify any gym equipment visible.
For each equipment found, provide the name and confidence level (0-1).
Focus on common gym equipment like dumbbells, barbells, benches, machines, etc.
Format your response as a list with equipment names and confidence scores.
Example format:
Equipment: Dumbbell (0.95)
Equipment: Bench Press (0.87)""", pil_image]
        )
        response_text = response.text

        # Extract equipment information
        equipment_list = _extract_equipment_names(response_text)
        primary_equipment = _get_primary_equipment(equipment_list)

        return EquipmentScanResponse(
            success=True,
            equipment_detected=equipment_list,
            primary_equipment=primary_equipment
        )

    except Exception as e:
        return EquipmentScanResponse(
            success=False,
            equipment_detected=[],
            error_message=f"Failed to process image: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for AI service"""
    return {"status": "healthy", "service": "AI Equipment Detection"}
