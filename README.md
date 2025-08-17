ConnectRandom - Setup Guide
---------------------------

1. Create virtual environment:
   python -m venv venv

2. Activate virtual environment:
   Windows: venv\Scripts\activate
   Linux/Mac: source venv/bin/activate

3. Install dependencies:
   pip install flask flask-cors uvicorn asgiref smtplib email

4. Run the server:
   uvicorn main:asgi_app --reload

App will be available at: http://127.0.0.1:8000
