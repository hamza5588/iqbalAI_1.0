# AI Teaching Assistant Application

## Project Structure
```
project/
├── app/
│   ├── routes/         # Route handlers
│   ├── models/         # Data models
│   ├── services/       # Business logic
│   ├── utils/          # Utility functions
│   └── static/         # Static files
├── templates/          # HTML templates
└── requirements.txt    # Project dependencies
```

## Setup Instructions
1. Create a virtual environment: `python -m venv venv`
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Initialize database: `flask init-db`
5. Run the application: `flask run`

## Features
- User authentication
- Real-time chat interface
- File upload and processing
- Voice input/output
- Custom prompt management
