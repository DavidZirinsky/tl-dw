import json
from lambda_function import lambda_handler

# Simulate a Lambda event object
# Replace 'YOUR_YOUTUBE_VIDEO_URL' with an actual YouTube video URL
event = {
    "queryStringParameters": {
        "url": "https://www.youtube.com/watch?v=LCEmiRjPEtQ" # Example URL
    }
}

# Simulate a Lambda context object (can be an empty object for this case)
context = {}

# Invoke the lambda_handler
print("Invoking lambda_handler locally...")
response = lambda_handler(event, context)

# Process the response
import types

# Process the response
if isinstance(response.get('body'), types.GeneratorType): # Check if it's a generator object
    print("Streaming response detected:")
    full_summary = ""
    for chunk in response['body']: # Iterate over the generator directly
        decoded_chunk = chunk.decode('utf-8')
        print(decoded_chunk, end='') # Print chunks as they arrive
        full_summary += decoded_chunk
    print("\n--- End of Stream ---")
    print(f"Full Summary Length: {len(full_summary)} characters")
else:
    print("Non-streaming response:")
    print(json.dumps(response, indent=2))
