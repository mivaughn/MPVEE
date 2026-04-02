"""
Test Snowflake connection via Okta SSO.
Run this to verify your Okta → Snowflake authentication works.
"""

import os
import sys

import snowflake.connector

def test_connection():
    print("Testing Snowflake connection (Okta SSO)...")
    print("A browser window will open for authentication.\n")

    try:
        conn = snowflake.connector.connect(
            user=os.environ.get('SNOWFLAKE_USER') or 'MIVAUGHN',
            account=os.environ.get('SNOWFLAKE_ACCOUNT') or 'SOFI-SOFI',
            warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE') or 'DEFAULT',
            database=os.environ.get('SNOWFLAKE_DATABASE') or 'TDM_MEMBER',
            schema=os.environ.get('SNOWFLAKE_SCHEMA') or 'MODELED',
            authenticator='externalbrowser',
            client_store_temporary_credential=True,
        )

        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]
        cursor.execute("SELECT CURRENT_USER()")
        user = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        print("✓ Connection successful!")
        print(f"  Snowflake version: {version}")
        print(f"  Connected as: {user}")
        return 0

    except snowflake.connector.errors.DatabaseError as e:
        print(f"✗ Connection failed: {e}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(test_connection())
