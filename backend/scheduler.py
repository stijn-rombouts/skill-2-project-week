"""
Scheduler voor medicijn controle
Voert periodiek check uit of medicijnen zijn ingeslikt
"""

import schedule
import time
from database import SessionLocal
from medication_checker import check_missed_medications


def run_medication_checker():
    """Run the medication checker every day at 09:00"""
    db = SessionLocal()
    try:
        print(f"🔔 Running medication check...")
        check_missed_medications(db)
    finally:
        db.close()


def start_scheduler():
    """Start the scheduler in a background thread"""
    # Check every day at 9 AM
    schedule.every().day.at("09:00").do(run_medication_checker)
    
    # Also check every 6 hours as backup
    schedule.every(6).hours.do(run_medication_checker)
    
    print("⏰ Scheduler started - checking medications every 6 hours and at 09:00")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute if a scheduled task needs to run


if __name__ == "__main__":
    start_scheduler()
