#!/usr/bin/env python3

# Add file transfer methods to S3Agent
import os

s3_file = "/Users/tar/Desktop/SevaAI/seva-agent/agents/s3_agent.py"

# Read the file
with open(s3_file, 'r') as f:
    content = f.read()

# Add file transfer methods at the end
file_methods = '''
    def _upload_file_to_s3(self, command: str) -> Dict[str, Any]:
        try:
            import os
            
            # Parse: upload file /path/to/file.txt to bucket BUCKETNAME
            words = command.split()
            
            # Find file path (after "file")
            file_path = None
            for i, word in enumerate(words):
                if word.lower() == "file" and i + 1 < len(words):
                    file_path = words[i + 1]
                    break
            
            if not file_path:
                return {"error": "File path required. Format: upload file /path/to/file.txt to bucket BUCKETNAME"}
            
            # Expand user path (~)
            file_path = os.path.expanduser(file_path)
            
            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}
            
            bucket_name = self._extract_bucket_name(command)
            if not bucket_name:
                return {"error": "Bucket name required. Format: upload file /path/to/file.txt to bucket BUCKETNAME"}
            
            # Get filename for S3 key
            filename = os.path.basename(file_path)
            
            s3 = self.session.client('s3')
            
            # Upload file
            with open(file_path, 'rb') as f:
                s3.upload_fileobj(f, bucket_name, filename)
            
            return {
                "service": "s3",
                "operation": "upload_file_to_s3",
                "bucket": bucket_name,
                "key": filename,
                "local_path": file_path,
                "result": f"File uploaded successfully from {file_path} to s3://{bucket_name}/{filename}"
            }
            
        except Exception as e:
            return {"error": f"Failed to upload file: {str(e)}"}
    
    def _download_file_from_s3(self, command: str) -> Dict[str, Any]:
        try:
            import os
            
            # Parse: download file FILENAME from bucket BUCKETNAME to /path/to/save/
            words = command.split()
            
            # Find filename (after "file")
            filename = None
            for i, word in enumerate(words):
                if word.lower() == "file" and i + 1 < len(words):
                    filename = words[i + 1]
                    break
            
            if not filename:
                return {"error": "Filename required. Format: download file FILENAME from bucket BUCKETNAME to /path/"}
            
            bucket_name = self._extract_bucket_name(command)
            if not bucket_name:
                return {"error": "Bucket name required. Format: download file FILENAME from bucket BUCKETNAME to /path/"}
            
            # Find destination path (after "to")
            dest_path = None
            for i, word in enumerate(words):
                if word.lower() == "to" and i + 1 < len(words):
                    dest_path = words[i + 1]
                    break
            
            if not dest_path:
                # Default to Downloads folder
                dest_path = os.path.expanduser("~/Downloads")
            else:
                dest_path = os.path.expanduser(dest_path)
            
            # Ensure destination directory exists
            os.makedirs(dest_path, exist_ok=True)
            
            # Full path for downloaded file
            local_file_path = os.path.join(dest_path, filename)
            
            s3 = self.session.client('s3')
            
            # Download file
            with open(local_file_path, 'wb') as f:
                s3.download_fileobj(bucket_name, filename, f)
            
            return {
                "service": "s3",
                "operation": "download_file_from_s3",
                "bucket": bucket_name,
                "key": filename,
                "local_path": local_file_path,
                "result": f"File downloaded successfully from s3://{bucket_name}/{filename} to {local_file_path}"
            }
            
        except Exception as e:
            return {"error": f"Failed to download file: {str(e)}"}'''

# Add methods before the last line
if '_upload_file_to_s3' not in content:
    content = content.rstrip() + file_methods

# Write back
with open(s3_file, 'w') as f:
    f.write(content)

print("✅ Added file transfer methods to S3Agent")

# Update orchestrator for response formatting
orch_file = "/Users/tar/Desktop/SevaAI/seva-agent/orchestrator.py"

with open(orch_file, 'r') as f:
    orch_content = f.read()

# Add response formatting
file_response = '''        elif service == "s3" and operation in ["upload_file_to_s3", "download_file_from_s3"]:
            bucket = result.get("bucket")
            key = result.get("key")
            local_path = result.get("local_path")
            if operation == "upload_file_to_s3":
                return f"{agent_header}⬆️ Uploaded '{key}' from {local_path} to bucket '{bucket}'"
            else:
                return f"{agent_header}⬇️ Downloaded '{key}' from bucket '{bucket}' to {local_path}"
        '''

if 'upload_file_to_s3' not in orch_content:
    # Find the default formatting line and add before it
    orch_content = orch_content.replace(
        '        # Default formatting',
        file_response + '\n        # Default formatting'
    )

with open(orch_file, 'w') as f:
    f.write(orch_content)

print("✅ Added file transfer response formatting to orchestrator")