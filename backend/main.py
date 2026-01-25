from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

notification_schedule = []

def generate_notification_schedule():
    global notification_schedule
    # Generate the notification schedule, scheduled every 20 seconds for 1 hour
    from datetime import datetime, timedelta
    now = datetime.now()
    notification_schedule = []
    for i in range(180):
        notification_time = now + timedelta(seconds=20 * (i + 1))
        notification_schedule.append({
            "time": notification_time.strftime("%H:%M:%S"),
            "timestamp": notification_time.isoformat(),
            "message": f"Notification {i + 1} at {notification_time.strftime('%H:%M:%S')}"
        })

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/api/check")
async def check():
    return True

# Schedule for notifications
@app.get("/api/schedule_notification")
async def schedule_notification():    
    return {"schedule": notification_schedule}

# Endpoint to clear the schedule (for testing purposes)
@app.post("/api/clear_schedule")
async def clear_schedule():
    global notification_schedule
    notification_schedule = []
    return {"message": "Schedule cleared"}

@app.post("/api/generate_schedule")
async def regenerate_schedule():
    generate_notification_schedule()
    return {"message": "Schedule regenerated"}