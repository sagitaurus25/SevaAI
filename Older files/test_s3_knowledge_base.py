import boto3
import json
from decimal import Decimal
import argparse

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'S3CommandKnowledgeBase'

def query_knowledge_base(query):
    """Query the knowledge base with a user message"""
    try:
        table = dynamodb.Table(TABLE_NAME)
        
        # Scan the table for patterns that might match
        response = table.scan()
        
        best_match = None
        best_match_score = 0
        
        # Simple pattern matching
        query_lower = query.lower()
        
        print(f"\nQuerying: '{query}'")
        print("-" * 50)
        
        for item in response.get('Items', []):
            # Check exact intent match
            if item['intent_pattern'] in query_lower:
                print(f"✅ Exact match found: {item['intent_pattern']}")
                return item
            
            # Check example phrases
            for phrase in item.get('example_phrases', []):
                if phrase in query_lower:
                    print(f"✅ Example phrase match: {phrase}")
                    return item
            
            # Simple word overlap scoring
            pattern_words = set(item['intent_pattern'].lower().split())
            message_words = set(query_lower.split())
            common_words = pattern_words.intersection(message_words)
            
            if len(common_words) > 0:
                score = len(common_words) / len(pattern_words)
                print(f"Pattern: '{item['intent_pattern']}', Score: {score:.2f}")
                if score > best_match_score and score > 0.5:  # Threshold
                    best_match_score = score
                    best_match = item
        
        if best_match:
            print(f"\n✅ Best match: '{best_match['intent_pattern']}' with score {best_match_score:.2f}")
            return best_match
        else:
            print("\n❌ No good match found")
            return None
        
    except Exception as e:
        print(f"Error querying knowledge base: {str(e)}")
        return None

def display_result(result):
    """Display the result in a readable format"""
    if not result:
        return
    
    print("\nMatch Details:")
    print("-" * 50)
    print(f"Intent Pattern: {result['intent_pattern']}")
    print(f"Service: {result['service']}")
    print(f"Action: {result['action']}")
    print(f"Required Parameters: {', '.join(result['required_params']) if result['required_params'] else 'None'}")
    
    if result.get('needs_followup'):
        print(f"Needs Followup: Yes")
        print(f"Followup Question: {result.get('followup_question', 'None')}")
    else:
        print(f"Needs Followup: No")
    
    print(f"Syntax Template: {result.get('syntax_template', 'None')}")
    print("-" * 50)

def list_all_patterns():
    """List all patterns in the knowledge base"""
    try:
        table = dynamodb.Table(TABLE_NAME)
        response = table.scan()
        
        print("\nAll Knowledge Base Patterns:")
        print("-" * 50)
        
        for item in response.get('Items', []):
            print(f"• {item['intent_pattern']} → {item['service']}.{item['action']}")
        
    except Exception as e:
        print(f"Error listing patterns: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Test the S3 command knowledge base')
    parser.add_argument('--query', '-q', help='Query to test against the knowledge base')
    parser.add_argument('--list', '-l', action='store_true', help='List all patterns in the knowledge base')
    
    args = parser.parse_args()
    
    if args.list:
        list_all_patterns()
        return
    
    if args.query:
        result = query_knowledge_base(args.query)
        display_result(result)
    else:
        # Interactive mode
        print("S3 Command Knowledge Base Tester")
        print("Type 'exit' to quit, 'list' to see all patterns")
        
        while True:
            query = input("\nEnter a query: ")
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'list':
                list_all_patterns()
            else:
                result = query_knowledge_base(query)
                display_result(result)

if __name__ == "__main__":
    main()