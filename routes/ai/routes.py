import base64
import os
import re
from typing import List, Optional

import google.genai as genai
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
import io
from openai import OpenAI

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

# Initialize AI clients based on provider
gemini_client = None
openai_client = None

if settings.AI_PROVIDER == "gemini":
    if not settings.GEMINI_API_KEY:
        print("[AI] WARNING: GEMINI_API_KEY not found in settings. AI endpoints will not work until configured.")
    else:
        gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
elif settings.AI_PROVIDER == "openai":
    if not settings.OPENAI_API_KEY:
        print("[AI] WARNING: OPENAI_API_KEY not found in settings. AI endpoints will not work until configured.")
    else:
        openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _generate_ai_response(prompt: str, image=None) -> str:
    """Generate AI response using configured provider"""
    if settings.AI_PROVIDER == "openai":
        if not openai_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI client not configured. Set OPENAI_API_KEY in your environment."
            )
        if image:
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
                    ]
                }]
            )
            return response.choices[0].message.content
        else:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
    else:
        if not gemini_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini client not configured. Set GEMINI_API_KEY in your environment."
            )
        if image:
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[prompt, image]
            )
        else:
            response = gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
        return response.text


def _extract_equipment_names(response_text: str) -> List[EquipmentDetection]:
    """Extract equipment names and confidence from AI response"""
    equipment_dict = {}  # Use dict to avoid duplicates
    
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
                confidence = confidence / 100.0
            
            if name and confidence > 0.3:
                # Keep highest confidence if duplicate
                if name not in equipment_dict or equipment_dict[name] < confidence:
                    equipment_dict[name] = min(confidence, 1.0)
    
    # Convert dict to list
    equipment_list = [
        EquipmentDetection(name=name, confidence=conf, description=None)
        for name, conf in equipment_dict.items()
    ]
    
    return equipment_list


def _get_primary_equipment(equipment_list: List[EquipmentDetection]) -> Optional[str]:
    """Get the equipment with highest confidence"""
    if not equipment_list:
        return None
    
    primary = max(equipment_list, key=lambda x: x.confidence)
    return primary.name if primary.confidence > 0.5 else None


@router.post("/scan-equipment-upload", response_model=EquipmentScanResponse)
async def scan_equipment_image_upload(
    image: UploadFile = File(..., description="Image file to scan for equipment detection")
):
    """
    Scan an uploaded image file to identify gym equipment from database
    """
    try:
        from applications.equipments.models import Equipment
        
        # Get all equipment from database
        equipment_list_db = await Equipment.all().values('id', 'name', 'description')
        
        if not equipment_list_db:
            return EquipmentScanResponse(
                success=False,
                equipment_detected=[],
                error_message="No equipment found in database"
            )
        
        equipment_names = [eq['name'] for eq in equipment_list_db]
        equipment_names_str = ", ".join(equipment_names)
        
        image_bytes = await image.read()
        pil_image = Image.open(io.BytesIO(image_bytes))

        prompt = f"""Analyze this image and identify gym equipment visible.
Only detect equipment from this list: {equipment_names_str}

For each equipment found from the list, provide the name (exactly as listed) and confidence level (0-1).
If no equipment from the list is visible, respond with "No equipment found".

Format your response as:
Equipment: [exact name from list] (confidence)
Example:
Equipment: Dumbbell (0.95)
Equipment: Bench Press (0.87)"""
        
        response_text = _generate_ai_response(prompt, pil_image)

        if "no equipment found" in response_text.lower():
            return EquipmentScanResponse(
                success=True,
                equipment_detected=[],
                primary_equipment=None,
                error_message="This equipment is not found in this gym"
            )

        equipment_detected = _extract_equipment_names(response_text)
        
        # Filter only equipment that exists in database
        valid_equipment = []
        for eq in equipment_detected:
            # Case-insensitive matching
            matched = next((db_eq for db_eq in equipment_list_db 
                          if db_eq['name'].lower() == eq.name.lower()), None)
            if matched:
                valid_equipment.append(EquipmentDetection(
                    name=matched['name'],
                    confidence=eq.confidence,
                    description=matched.get('description')
                ))
        
        if not valid_equipment:
            return EquipmentScanResponse(
                success=True,
                equipment_detected=[],
                primary_equipment=None,
                error_message="This equipment is not found in this gym"
            )
        
        primary_equipment = _get_primary_equipment(valid_equipment)

        return EquipmentScanResponse(
            success=True,
            equipment_detected=valid_equipment,
            primary_equipment=primary_equipment
        )

    except Exception as e:
        return EquipmentScanResponse(
            success=False,
            equipment_detected=[],
            error_message=f"Failed to process image: {str(e)}"
        )

