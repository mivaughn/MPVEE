"""
Snowflake connection script - runs invitable users query and exports to CSV.
Set credentials via environment variables before running.
"""

import csv
import os
from datetime import datetime

import snowflake.connector

# Connection: use PAT if SNOWFLAKE_TOKEN set (for cloud), else SSO (for local)
_conn_params = {
    'user': os.environ.get('SNOWFLAKE_USER') or 'MIVAUGHN',
    'account': os.environ.get('SNOWFLAKE_ACCOUNT') or 'SOFI-SOFI',
    'warehouse': os.environ.get('SNOWFLAKE_WAREHOUSE', 'DEFAULT'),
    'database': os.environ.get('SNOWFLAKE_DATABASE', 'TDM_MEMBER'),
    'schema': os.environ.get('SNOWFLAKE_SCHEMA', 'MODELED'),
}
_pat = os.environ.get('SNOWFLAKE_TOKEN') or os.environ.get('SNOWFLAKE_PAT')
if _pat:
    _conn_params['password'] = _pat
else:
    _conn_params['authenticator'] = 'externalbrowser'
    _conn_params['client_store_temporary_credential'] = True
conn = snowflake.connector.connect(**_conn_params)

MAIN_QUERY = """
WITH invitable_users AS (
    
    SELECT
        e.PARTY_ID
        ,e.EMAIL
        ,u.UNSUBSCRIBE_HASH
    FROM
        (
            SELECT
                PARTY_ID
                ,EMAIL_ADDR AS EMAIL
           FROM TDM_CUSTOMERS.CLEANSED.CUSTOMERS_EMAIL
           WHERE EFFECTIVE_END_DT IS NULL
                AND EMAIL_ADDR IS NOT NULL
        ) AS e
    INNER JOIN
        (
            SELECT 
                a.USER_ID
            FROM TDM_EDW_MEMBER.SUMMARIZED.MEMBER_SUMMARY_DAILY a
            LEFT JOIN 
                (
                    SELECT
                        USER_ID
                        ,COALESCE(EVER_AN_EMPLOYEE, FALSE) as ever_an_employee
                    FROM TDM_EDW_MEMBER.SUMMARIZED.MEMBER_ATTRIBUTE_SUMMARY_DEDUPED
                    QUALIFY row_number() OVER (PARTITION BY USER_ID ORDER BY REGISTRATION_COMPLETE_DATE_UTC DESC) = 1
                ) b
                ON a.USER_ID::VARCHAR = b.USER_ID::VARCHAR
            WHERE REPORTING_DATE = (SELECT MAX(REPORTING_DATE) FROM TDM_EDW_MEMBER.SUMMARIZED.MEMBER_SUMMARY_DAILY)
                AND (COALESCE(SOFI_EMPLOYEE_IND, FALSE) AND COALESCE(ever_an_employee, FALSE)) = FALSE

        ) as s
        ON e.PARTY_ID::VARCHAR = s.USER_ID::VARCHAR
    INNER JOIN
        (
            SELECT 
                PARTY_ID
            FROM TDM_COMMUNICATIONS.CLEANSED.NOTIFICATION_PREFERENCES_PREFERENCE
            WHERE EFFECTIVE_END_DT IS NULL
            GROUP BY 1
            HAVING 
                (
                    SUM(CASE WHEN PREFERENCE_TYPE = 'DO_NOT_CONTACT'  THEN 1 ELSE 0 END) = 0
                    OR
                    (
                        SUM(CASE WHEN PREFERENCE_TYPE = 'DO_NOT_CONTACT' THEN 1 ELSE 0 END) = 1
                        AND
                        SUM(CASE WHEN PREFERENCE_TYPE = 'DO_NOT_CONTACT' AND OPT_PREFERENCE = 'OPT_OUT' THEN 1 ELSE 0 END) = 1

                    )
                
                )
        ) as dnc
        ON e.PARTY_ID::VARCHAR = dnc.PARTY_ID::VARCHAR
    INNER JOIN
        (
            SELECT
                PARTY_ID
            FROM TDM_COMMUNICATIONS.CLEANSED.NOTIFICATION_PREFERENCES_PREFERENCE
            WHERE EFFECTIVE_END_DT IS NULL
                AND PREFERENCE_TYPE = 'MARKETING_EMAIL'
                AND COALESCE(OPT_PREFERENCE,'OPT_IN') = 'OPT_IN'
        ) AS dnm
        ON e.PARTY_ID::VARCHAR = dnm.PARTY_ID::VARCHAR
    INNER JOIN
        (
            SELECT 
                USER_ID
            FROM TDM_PRIVACY.CROSS_AFFILIATES.USER_AFFILIATE_LOOKUP
            GROUP BY 1
            HAVING BOOLOR_AGG(AFFILIATE_ACCESS_ALLOWED) = TRUE
        ) as a
        ON e.PARTY_ID::VARCHAR = a.USER_ID::VARCHAR
    INNER JOIN 
        (
            SELECT
                PARTY_ID
                ,VALUE AS UNSUBSCRIBE_HASH
            FROM TDM_COMMUNICATIONS.CLEANSED.BRAZEPROXY_COMMAND_UPDATE_CUSTOMER_ATTRIBUTES
            WHERE ATTRIBUTE = 'unsubscribe_hash'
            QUALIFY row_number() OVER (PARTITION BY PARTY_ID ORDER BY EVENT_TIME DESC) = 1
        ) AS u
        ON e.PARTY_ID::VARCHAR = u.PARTY_ID::VARCHAR
            AND u.UNSUBSCRIBE_HASH IS NOT NULL
)

,l37 AS (
    SELECT 
        USER_ID
        ,SUM(D1_USAGE) as n_active_days 
    FROM TDM_MEMBER.MODELED.ACTIVITY_SUMMARY_ALL
    WHERE datediff(DAY, DT, current_date()) BETWEEN 0 AND 7 
    GROUP BY 1
    HAVING SUM(D1_USAGE) >= 3
)

,population AS (
    SELECT
        e.PARTY_ID
        ,e.EMAIL
        ,e.UNSUBSCRIBE_HASH
        ,l.n_active_days
        ,row_number() OVER(ORDER BY random()) as n_sample
    FROM invitable_users as e
    INNER JOIN l37 l
        ON e.PARTY_ID::VARCHAR = l.USER_ID::VARCHAR
)

SELECT 
    EMAIL
    ,UNSUBSCRIBE_HASH
FROM population WHERE n_sample <= 300
"""

try:
    cursor = conn.cursor()

    # Enable secondary roles for cross-database access
    cursor.execute("USE SECONDARY ROLES ALL")
    # Execute main query
    cursor.execute(MAIN_QUERY)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    if not rows:
        print("Query returned 0 rows. No CSV file created.")
    else:
        # Export to CSV - use absolute path so file always goes next to script
        script_dir = os.path.abspath(os.path.dirname(__file__))
        output_dir = os.path.join(script_dir, 'snowflake_exports')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"invitable_users_{datetime.now().strftime('%Y-%m-%d')}.csv")
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        # Use absolute path in output so user can locate file regardless of cwd
        abs_output_path = os.path.abspath(output_path)
        print(f"Exported {len(rows)} rows to {abs_output_path}")

    cursor.close()
except (snowflake.connector.errors.ProgrammingError, snowflake.connector.errors.DatabaseError) as e:
    err_msg = str(e).lower()
    if any(x in err_msg for x in ('token', 'authenticate', 'idp', 'sso', 'credential', 'login', 'user differs')):
        print("\n⚠️  SSO failed or token expired. Run this script manually to log in again:")
        print("   python3 snowflake_connect.py\n")
    print(f"Error: {e}")
    raise
except Exception as e:
    print(f"Error: {e}")
    raise
finally:
    conn.close()
