# test_mysql.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.database import DatabaseManager

def test_database():
    print("🧪 Kiểm tra kết nối MySQL...")
    
    db = DatabaseManager()
    
    # Test đăng ký
    print("\n1. Testing đăng ký user...")
    success, message = db.register_user("test_user", "test_password")
    print(f"   Kết quả: {success} - {message}")
    
    # Test đăng nhập
    print("\n2. Testing đăng nhập...")
    success, message, user_data = db.login_user("test_user", "test_password")
    print(f"   Kết quả: {success} - {message}")
    if user_data:
        print(f"   User data: {user_data}")
    
    # Test đăng nhập sai
    print("\n3. Testing đăng nhập sai...")
    success, message, user_data = db.login_user("test_user", "wrong_password")
    print(f"   Kết quả: {success} - {message}")
    
    db.close()

if __name__ == "__main__":
    test_database()