import sys
import time
from playwright.sync_api import sync_playwright

if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8')

def send_notification(game_code, period):
    with sync_playwright() as p:
        print("[*] Khởi động trình duyệt Playwright...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("[*] Truy cập Portal 28091...")
        page.goto("http://172.16.9.29:28091/auth/login")
        
        # Đoạn này xử lý Login nếu bị văng ra
        try:
            page.wait_for_selector("input[formcontrolname='username']", timeout=5000)
            print("[*] Đang Đăng nhập...")
            page.locator("input[formcontrolname='username']").fill("ctinadmin")
            page.locator("input[formcontrolname='password']").fill("ctin@123456")
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(3000) # Cho thoi gian de he thong xac thuc
            page.wait_for_load_state('networkidle')
        except Exception as e:
            pass # Co the da login
            
        print("[*] Chuyển đến trang Danh sách Thông báo Trúng thưởng...")
        page.goto("http://172.16.9.29:28091/dashboard/reward-management/winning-notification/list", wait_until='networkidle')
        
        # Tu dong accept tat ca cac dialog confirm
        page.on('dialog', lambda dialog: dialog.accept())
        page.wait_for_timeout(5000) # Cho han 5 giay de chac chan render
        
        # Luu DOM de debug
        dom_file = "d:\\2026\\VLT Antigravity\\scripts\\giả lập trúng thưởng\\dom_28091.html"
        with open(dom_file, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"[*] Đã lưu mã nguồn trang web hiện tại vào: {dom_file}")

        
        print("[*] Đang chờ nút 'Gửi TBTT' xuất hiện...")
        try:
            buttons = page.locator("button:has-text('Gửi TBTT')")
            if buttons.count() > 0:
                print(f"[*] Tìm thấy {buttons.count()} nút. Đang click nút đầu tiên (kỳ quay mới nhất)...")
                buttons.first.click()
                print("[OK] ĐÃ CLICK THÀNH CÔNG NÚT 'Gửi TBTT'!")
                time.sleep(3) # Cho load ket qua
            else:
                print("[LỖI] Không thấy nút Gửi TBTT nào khả dụng.")
        except Exception as e:
            print(f"[LỖI] Click thất bại: {e}")


        browser.close()

if __name__ == "__main__":
    game = sys.argv[1] if len(sys.argv) > 1 else "645"
    period = sys.argv[2] if len(sys.argv) > 2 else "00534"
    send_notification(game, period)
