#!/usr/bin/env python3

# Add file transfer methods to S3Agent properly
s3_file = "/Users/tar/Desktop/SevaAI/seva-agent/agents/s3_agent.py"

methods = '''
    def _upload_file_to_s3(self, command: str) -> Dict[str, Any]:
        try:
            words = command.split()
            
            file_path = None
            for i, word in enumerate(words):
                if word.lower() == "file" and i + 1 < len(words):
                    file_path = words[i + 1]
                    break
            
            if not file_path:
                return {"error": "File path required"}
            
            file_info = fs.get_file_info(file_path)
            if not file_info["success"]:
                return {"error": f"File not found: {file_path}"}
            
            bucket_name = self._extract_bucket_name(command)
            if not bucket_name:
                return {"error": "Bucket name required"}
            
            filename = os.path.basename(file_path)
            
            file_content = fs.read_binary_file(file_path)
            if not file_content["success"]:
                return {"error": f"Failed to read file: {file_content['error']}"}
            
            s3 = self.session.client("s3")
            s3.put_object(Bucket=bucket_name, Key=filename, Body=file_content["content"])
            
            return {
                "service": "s3",
                "operation": "upload_file_to_s3",
                "bucket": bucket_name,
                "key": filename,
                "local_path": file_path,
                "size": file_info["size"],
                "result": "File uploaded successfully"
            }
            
        except Exception as e:
            return {"error": f"Failed to upload file: {str(e)}"}
    
    def _download_file_from_s3(self, command: str) -> Dict[str, Any]:
        try:
            words = command.split()
            
            filename = None
            for i, word in enumerate(words):
                if word.lower() == "file" and i + 1 < len(words):
                    filename = words[i + 1]
                    break
            
            if not filename:
                return {"error": "Filename required"}
            
            bucket_name = self._extract_bucket_name(command)
            if not bucket_name:
                return {"error": "Bucket name required"}
            
            dest_path = "~/Downloads"
            local_file_path = os.path.join(os.path.expanduser(dest_path), filename)
            
            s3 = self.session.client("s3")
            response = s3.get_object(Bucket=bucket_name, Key=filename)
            file_content = response["Body"].read()
            
            write_result = fs.write_binary_file(local_file_path, file_content)
            if not write_result["success"]:
                return {"error": f"Failed to write file: {write_result['error']}"}
            
            return {
                "service": "s3",
                "operation": "download_file_from_s3",
                "bucket": bucket_name,
                "key": filename,
                "local_path": local_file_path,
                "size": len(file_content),
                "result": "File downloaded successfully"
            }
            
        except Exception as e:
            return {"error": f"Failed to download file: {str(e)}"}'''

with open(s3_file, 'a') as f:
    f.write(methods)

print("✅ Added file transfer methods to S3Agent")