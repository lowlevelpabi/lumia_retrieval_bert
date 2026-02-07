import traceback
import sys

print("Python version:", sys.version)

try:
    print("Attempting to import app.main...")
    from app.main import app
    print("\nSUCCESS: App loaded successfully!")
except Exception as e:
    print("\n--- CRITICAL ERROR DURING STARTUP ---")
    traceback.print_exc()
    sys.exit(1)
finally:
    print("\n--- Script Finished ---")
