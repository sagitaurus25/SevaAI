#!/usr/bin/env python3

import boto3
import json
import zipfile
import io
import os
import time
from datetime import datetime

# Lambda function name
FUNCTION_NAME = 'SevaAI-S3Agent'
BACKUP_DIR = 'lambda_backups'

def backup_lambda():
    """Backup the current Lambda function code"""
    print(f"Backing up Lambda function: {FUNCTION_NAME}")
    
    try:
        # Create backup directory if it doesn't exist
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # Get the current Lambda function code
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
        code_location = response['Code']['Location']
        
        # Download the current code
        import requests
        r = requests.get(code_location)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{BACKUP_DIR}/{FUNCTION_NAME}_{timestamp}.zip"
        
        # Save the backup
        with open(backup_file, 'wb') as f:
            f.write(r.content)
        
        # Extract the code for reference
        extract_dir = f"{BACKUP_DIR}/{FUNCTION_NAME}_{timestamp}"
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(backup_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        print(f"✅ Lambda function backed up to: {backup_file}")
        print(f"✅ Code extracted to: {extract_dir}")
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Error backing up Lambda function: {str(e)}")
        return None

def list_backups():
    """List all available backups"""
    if not os.path.exists(BACKUP_DIR):
        print("No backups found.")
        return []
    
    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.zip')]
    backups.sort(reverse=True)  # Most recent first
    
    print("Available backups:")
    for i, backup in enumerate(backups):
        print(f"{i+1}. {backup}")
    
    return backups

def restore_lambda(backup_file=None):
    """Restore Lambda function from a backup"""
    if not backup_file:
        backups = list_backups()
        if not backups:
            print("No backups available to restore.")
            return False
        
        choice = input("Enter the number of the backup to restore (or press Enter for the most recent): ")
        if choice.strip():
            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    backup_file = f"{BACKUP_DIR}/{backups[index]}"
                else:
                    print("Invalid selection.")
                    return False
            except ValueError:
                print("Invalid input. Please enter a number.")
                return False
        else:
            backup_file = f"{BACKUP_DIR}/{backups[0]}"  # Most recent
    
    print(f"Restoring Lambda function from: {backup_file}")
    
    try:
        # Read the backup file
        with open(backup_file, 'rb') as f:
            zip_content = f.read()
        
        # Update the Lambda function
        lambda_client = boto3.client('lambda')
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content,
            Publish=True
        )
        
        print(f"✅ Lambda function restored successfully")
        print(f"Version: {response.get('Version')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error restoring Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 backup_restore_lambda.py [backup|list|restore]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'backup':
        backup_lambda()
    elif command == 'list':
        list_backups()
    elif command == 'restore':
        backup_file = sys.argv[2] if len(sys.argv) > 2 else None
        restore_lambda(backup_file)
    else:
        print("Unknown command. Use 'backup', 'list', or 'restore'.")