#!/usr/bin/env python3
"""
Setup and run script for audio processing.
This script helps you set up the environment and run the audio cutting process.
"""

import os
import sys
import subprocess

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    return missing_vars

def setup_environment():
    """Interactive setup of environment variables"""
    print("🔧 Setting up environment variables...")
    
    supabase_url = input("Enter your Supabase URL (e.g., https://your-project.supabase.co): ").strip()
    if not supabase_url:
        print("❌ Supabase URL is required")
        return False
    
    supabase_key = input("Enter your Supabase Service Key: ").strip()
    if not supabase_key:
        print("❌ Supabase Service Key is required")
        return False
    
    # Set environment variables for this session
    os.environ['SUPABASE_URL'] = supabase_url
    os.environ['SUPABASE_SERVICE_KEY'] = supabase_key
    
    print("✅ Environment variables set for this session")
    return True

def main():
    print("🎯 Audio Processing Setup for Run 3afe854f-6cf6-403e-b2b2-77e039b6f8ca")
    print("=" * 70)
    
    # Check if environment variables are already set
    missing_vars = check_environment()
    
    if missing_vars:
        print(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("\nYou can either:")
        print("1. Set them manually in your shell:")
        print("   export SUPABASE_URL='https://your-project.supabase.co'")
        print("   export SUPABASE_SERVICE_KEY='your-service-key'")
        print("\n2. Or run this script interactively to set them now.")
        
        choice = input("\nWould you like to set them interactively now? (y/n): ").strip().lower()
        if choice == 'y':
            if not setup_environment():
                return 1
        else:
            print("❌ Please set the environment variables and run the script again")
            return 1
    else:
        print("✅ Environment variables are already set")
    
    # Check if we're in the right directory
    if not os.path.exists('scripts/process_specific_run.py'):
        print("❌ Please run this script from the hoptix-flask directory")
        return 1
    
    # Run the audio processing script
    print("\n🚀 Starting audio processing...")
    try:
        result = subprocess.run([
            sys.executable, 'scripts/process_specific_run.py'
        ], check=True)
        print("🎉 Audio processing completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Audio processing failed with exit code {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n⏹️ Process interrupted by user")
        return 1

if __name__ == "__main__":
    exit(main())
