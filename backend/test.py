"""
Debug script for Neo4j Aura connection.
Based on official Neo4j Python driver documentation.
"""

import os
from neo4j import GraphDatabase


def debug_connection():
    """Test connection with official Neo4j approach."""
    
    # Load from environment (as per official docs)
    URI = os.getenv("NEO4J_URI")
    USERNAME = os.getenv("NEO4J_USERNAME")
    PASSWORD = os.getenv("NEO4J_PASSWORD")
    DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
    
    # Validate we have credentials
    if not all([URI, USERNAME, PASSWORD]):
        print("✗ Missing environment variables:")
        print(f"  NEO4J_URI: {URI}")
        print(f"  NEO4J_USERNAME: {USERNAME}")
        print(f"  NEO4J_PASSWORD: {'***' if PASSWORD else 'NOT SET'}")
        return False
    
    print("📋 Connection Details:")
    print(f"  URI: {URI}")
    print(f"  Username: {USERNAME}")
    print(f"  Database: {DATABASE}")
    print()
    
    # Create driver (official docs approach)
    print("🔗 Creating driver...")
    try:
        driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
        print("✓ Driver created")
    except Exception as e:
        print(f"✗ Failed to create driver: {e}")
        return False
    
    # Verify connectivity immediately (official docs)
    print("🔐 Verifying connectivity...")
    try:
        driver.verify_connectivity()
        print("✓ Connectivity verified")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        driver.close()
        return False
    
    # Test a simple query
    print("📊 Running test query...")
    try:
        with driver.session(database=DATABASE) as session:
            result = session.run("RETURN 1 as num")
            record = result.single()
            print(f"✓ Query succeeded: {record}")
    except Exception as e:
        print(f"✗ Query failed: {e}")
        driver.close()
        return False
    
    # Close properly
    driver.close()
    print("✓ Connection closed")
    print()
    print("✅ All checks passed!")
    return True


if __name__ == "__main__":
    # Load .env file if exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("📄 Loaded environment from .env file")
        print()
    except ImportError:
        print("⚠️  python-dotenv not installed, using environment variables")
        print()
    
    success = debug_connection()
    exit(0 if success else 1)