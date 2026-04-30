# Social Auth Frontend Integration

This guide explains how to use Google and Apple signup/signin with the current backend.

## Overview

The backend supports these endpoints:

- `POST /auth/google`
- `POST /auth/apple`

Both endpoints handle:

- signup for new users
- signin for existing users

The frontend only needs to get a provider `id_token` from Google or Apple, then send it to the backend.

## Backend Flow

### Google

1. Frontend authenticates the user with Google.
2. Google returns an `id_token`.
3. Frontend sends that token to `POST /auth/google`.
4. Backend verifies the token.
5. Backend finds or creates a local user.
6. Backend returns your app JWT tokens.

### Apple

1. Frontend authenticates the user with Apple.
2. Apple returns an `id_token`.
3. Frontend sends that token to `POST /auth/apple`.
4. Backend verifies the token against Apple keys.
5. Backend finds or creates a local user.
6. Backend returns your app JWT tokens.

## Required Backend Environment Variables

Set these in `.env`:

```env
GOOGLE_CLIENT_IDS=your-google-web-client-id.apps.googleusercontent.com
APPLE_CLIENT_IDS=your-apple-service-id-or-bundle-id
```

Notes:

- `GOOGLE_CLIENT_IDS` can contain one or more comma-separated client IDs.
- `APPLE_CLIENT_IDS` can contain one or more comma-separated app identifiers.
- The backend checks the token audience against these values.

## API Endpoints

### 1. Google Auth

**Endpoint**

```http
POST /auth/google
Content-Type: application/json
```

**Request body**

```json
{
  "id_token": "GOOGLE_ID_TOKEN"
}
```

**Success response**

```json
{
  "message": "User created successfully",
  "access_token": "your-access-token",
  "refresh_token": "your-refresh-token",
  "token_type": "bearer"
}
```

Or for existing users:

```json
{
  "message": "Login successful",
  "access_token": "your-access-token",
  "refresh_token": "your-refresh-token",
  "token_type": "bearer"
}
```

### 2. Apple Auth

**Endpoint**

```http
POST /auth/apple
Content-Type: application/json
```

**Request body**

```json
{
  "id_token": "APPLE_ID_TOKEN",
  "first_name": "Isaac",
  "last_name": "Hawi"
}
```

`first_name` and `last_name` are optional, but recommended on first Apple login because Apple may only send profile info once.

**Success response**

```json
{
  "message": "User created successfully",
  "access_token": "your-access-token",
  "refresh_token": "your-refresh-token",
  "token_type": "bearer"
}
```

Or for existing users:

```json
{
  "message": "Login successful",
  "access_token": "your-access-token",
  "refresh_token": "your-refresh-token",
  "token_type": "bearer"
}
```

## Frontend Integration Pattern

The frontend flow is the same for both providers:

1. Ask the provider SDK to sign in.
2. Get the provider `id_token`.
3. Send it to your backend.
4. Store returned `access_token` and `refresh_token`.
5. Use `access_token` in `Authorization: Bearer <token>` for authenticated API calls.

## Frontend Example With Fetch

### Google

```js
async function signInWithGoogle(idToken) {
  const response = await fetch("http://localhost:8000/auth/google", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      id_token: idToken,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Google auth failed");
  }

  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);

  return data;
}
```

### Apple

```js
async function signInWithApple(idToken, firstName = "", lastName = "") {
  const response = await fetch("http://localhost:8000/auth/apple", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      id_token: idToken,
      first_name: firstName || null,
      last_name: lastName || null,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Apple auth failed");
  }

  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);

  return data;
}
```

## React Example

This example only shows backend integration after the provider SDK gives you an `id_token`.

```jsx
async function handleGoogleSuccess(googleResponse) {
  const idToken = googleResponse.credential;

  const result = await fetch("http://localhost:8000/auth/google", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      id_token: idToken,
    }),
  });

  const data = await result.json();

  if (!result.ok) {
    throw new Error(data.detail || "Google login failed");
  }

  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
}
```

## Flutter Example

### Google

```dart
Future<Map<String, dynamic>> loginWithGoogle(String idToken) async {
  final response = await http.post(
    Uri.parse('http://localhost:8000/auth/google'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'id_token': idToken,
    }),
  );

  final data = jsonDecode(response.body);

  if (response.statusCode >= 400) {
    throw Exception(data['detail'] ?? 'Google auth failed');
  }

  return data;
}
```

### Apple

```dart
Future<Map<String, dynamic>> loginWithApple(
  String idToken, {
  String? firstName,
  String? lastName,
}) async {
  final response = await http.post(
    Uri.parse('http://localhost:8000/auth/apple'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'id_token': idToken,
      'first_name': firstName,
      'last_name': lastName,
    }),
  );

  final data = jsonDecode(response.body);

  if (response.statusCode >= 400) {
    throw Exception(data['detail'] ?? 'Apple auth failed');
  }

  return data;
}
```

## Token Storage

After successful social auth, store:

- `access_token`
- `refresh_token`

Example header for protected APIs:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
refresh-token: YOUR_REFRESH_TOKEN
```

## Get Current Logged-In User

Use:

```http
GET /auth/verify-token
```

Example:

```js
async function getCurrentUser() {
  const accessToken = localStorage.getItem("access_token");
  const refreshToken = localStorage.getItem("refresh_token");

  const response = await fetch("http://localhost:8000/auth/verify-token", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "refresh-token": refreshToken || "",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to verify token");
  }

  return data;
}
```

## Important Apple Notes

- Apple may not send email on every login.
- Apple may not send name on every login.
- The first login is the best time to capture `first_name`, `last_name`, and email.
- Your backend already prevents creating a brand-new Apple user without email on first login.

## Important Google Notes

- Google token must contain a verified email.
- The token audience must match one of the configured `GOOGLE_CLIENT_IDS`.

## Error Handling

Common backend error responses:

### Invalid token

```json
{
  "detail": "Invalid Google token."
}
```

or

```json
{
  "detail": "Invalid Apple token."
}
```

### Audience mismatch

```json
{
  "detail": "Google token audience mismatch."
}
```

or

```json
{
  "detail": "Apple token audience mismatch."
}
```

### Missing provider config

```json
{
  "detail": "GOOGLE_CLIENT_IDS is not configured."
}
```

or

```json
{
  "detail": "APPLE_CLIENT_IDS is not configured."
}
```

### Inactive user

```json
{
  "detail": "Inactive user"
}
```

## Recommended Frontend UX

- Show separate buttons:
  - `Continue with Google`
  - `Continue with Apple`
- Use the same backend flow for signup and signin.
- After successful response:
  - save tokens
  - fetch current user
  - redirect to dashboard or home page
- If auth fails:
  - show provider-specific message from backend

## Recommended Test Cases

Test these cases from frontend:

1. New Google user signs in for the first time.
2. Existing Google user signs in again.
3. New Apple user signs in for the first time.
4. Existing Apple user signs in again.
5. Invalid Google token.
6. Invalid Apple token.
7. Wrong audience in token.
8. User is inactive in backend.

## Backend Files Involved

- [routes/auth/routes.py](/abs/m:/MOYNUL/hawiisaac/routes/auth/routes.py:218)
- [app/utils/social_auth.py](/abs/m:/MOYNUL/hawiisaac/app/utils/social_auth.py:1)
- [applications/user/models.py](/abs/m:/MOYNUL/hawiisaac/applications/user/models.py:32)
- [app/config.py](/abs/m:/MOYNUL/hawiisaac/app/config.py:1)

## Final Notes

- Social signup and signin use the same endpoint.
- The frontend should never try to verify provider tokens itself for backend trust.
- The frontend only obtains the provider token and passes it to the backend.
- The backend is the source of truth for user creation, linking, and app JWT generation.
