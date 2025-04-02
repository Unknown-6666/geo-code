import os
import json

# Check if credentials are available
creds_env = os.environ.get('GOOGLE_CREDENTIALS')
creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

if creds_env:
    print("Credentials found in GOOGLE_CREDENTIALS environment variable")
    try:
        # Verify it's valid JSON
        creds_json = json.loads(creds_env)
        print("✅ GOOGLE_CREDENTIALS is valid JSON")
        
        # Check for required fields
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds_json]
        
        if missing_fields:
            print(f"❌ Missing required fields in credentials: {', '.join(missing_fields)}")
        else:
            print("✅ All required credential fields present")
            print(f"Service account: {creds_json.get('client_email')}")
            print(f"Project ID: {creds_json.get('project_id')}")
            
    except json.JSONDecodeError:
        print("❌ GOOGLE_CREDENTIALS is not valid JSON")
elif creds_file:
    print(f"✅ Credentials file found at: {creds_file}")
    try:
        with open(creds_file, 'r') as f:
            creds_json = json.load(f)
            print("✅ Credentials file contains valid JSON")
            print(f"Service account: {creds_json.get('client_email')}")
            print(f"Project ID: {creds_json.get('project_id')}")
    except Exception as e:
        print(f"❌ Error reading credentials file: {str(e)}")
else:
    print("❌ No credentials found!")

# Check other required environment variables
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
location = os.environ.get('VERTEX_LOCATION')
use_vertex = os.environ.get('USE_VERTEX_AI')

if project_id:
    print(f"✅ GOOGLE_CLOUD_PROJECT set to: {project_id}")
else:
    print("❌ GOOGLE_CLOUD_PROJECT not set")

if location:
    print(f"✅ VERTEX_LOCATION set to: {location}")
else:
    print("❌ VERTEX_LOCATION not set (will default to us-central1)")

if use_vertex:
    print(f"✅ USE_VERTEX_AI set to: {use_vertex}")
else:
    print("❌ USE_VERTEX_AI not set")

print("\nTo use Vertex AI, make sure to set up these secrets in your Replit environment:")
print("1. GOOGLE_CREDENTIALS - The full JSON content of your service account key")
print("2. GOOGLE_CLOUD_PROJECT - Your Google Cloud project ID")
print("3. VERTEX_LOCATION - Region for Vertex AI (e.g., us-central1)")
print("4. USE_VERTEX_AI - Set to 'true' to enable Vertex AI")