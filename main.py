import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    # Run the application
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)