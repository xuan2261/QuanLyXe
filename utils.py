import re
import html

def sanitize_input(input_string):
    """Loại bỏ các ký tự đặc biệt và các thẻ HTML khỏi chuỗi đầu vào."""
    # Xóa các thẻ HTML
    sanitized_string = re.sub('<[^<]+?>', '', input_string)
    # Chuyển đổi các ký tự đặc biệt thành các thực thể HTML tương ứng
    sanitized_string = html.escape(sanitized_string)
    return sanitized_string