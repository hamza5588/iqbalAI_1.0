from app import create_app
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = create_app()

if __name__ == '__main__':
    # Get port from command line argument or default to 5000
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)