import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend', '.env')
load_dotenv(dotenv_path)

# Build URL
url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(url)

sql = """
SELECT launch_site, count(*) as days_downloaded, 
       min(date) as from_date, max(date) as to_date
FROM era5_weather
GROUP BY launch_site;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql))
    print(f"{'Site':<15} | {'Days':<10} | {'From'} to {'To'}")
    print("-" * 50)
    for row in result:
        print(f"{row[0]:<15} | {row[1]:<10} | {row[2]} to {row[3]}")
