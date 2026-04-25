import os
import subprocess
import sys

SERVICES = [
    "api-gateway",
    "data-ingestion",
    "drift-monitor",
    "feature-engineering",
    "irrigation-controller",
    "model-server",
    "notification-service",
    "sensor-simulator",
    "user-service",
]

def run_tests():
    print("🚀 Starting Smart Irrigation Test Suite...")
    exit_code = 0
    
    for svc in SERVICES:
        test_dir = os.path.join("services", svc, "tests")
        if not os.path.exists(test_dir):
            continue
            
        print(f"\n▶ Testing {svc}...")
        
        # Build the command using python -m pytest directly
        cmd = [
            "python", "-m", "pytest", test_dir
        ]
        
        # Set PYTHONPATH to include the service source
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join("services", svc, "src")
        
        try:
            result = subprocess.run(cmd, env=env, check=False)
            if result.returncode != 0:
                exit_code = 1
        except Exception as e:
            print(f"❌ Error running tests for {svc}: {e}")
            exit_code = 1
            
    if exit_code == 0:
        print("\n✅ All test suites passed!")
    else:
        print("\n❌ Some test suites failed.")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    run_tests()
