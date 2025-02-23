from icrawler.builtin import GoogleImageCrawler
import cv2
from PIL import Image, ImageDraw, ImageFont
import os
import numpy as np
from nltk.corpus import wordnet
from googletrans import Translator
import eng_to_ipa as ipa
# 🔹 Hàm lấy loại từ chính
def get_word_type(word):
    synsets = wordnet.synsets(word)
    if not synsets:
        return "Unknown"  # Không xác định được loại từ
    pos = synsets[0].pos()  # Lấy loại từ của nghĩa đầu tiên
    pos_map = {"n": "Danh từ", "v": "Động từ", "a": "Tính từ", "r": "Trạng từ"}
    return pos_map.get(pos, "Khác")

# 🔹 Hàm dịch nghĩa sang tiếng Việt + lấy cách phát âm
def translate_word(word):
    translator = Translator()
    result = translator.translate(word, src="en", dest="vi")
    pronunciation = ipa.convert(word)  # Lấy phiên âm IPA
    return result.text, pronunciation

# 🔹 Nhập từ khóa
save_dir = "flashcards"
keyword = input("Nhập từ tiếng Anh: ")
print("\033[33mNhập những gì bạn biết về từ này hoặc bấm Enter để bỏ qua\033[0m")
word_type= input("Nhập loại từ (tính, danh, động, trạng,...): ")
define_vn = input("Nhập nghĩa tiếng Việt mà bạn biết: ")
subnet_dir =input("Nhập thư mục chủ đề bạn muốn tạo: ")
if not word_type:
    word_type = get_word_type(keyword)  # Xác định loại từ

if not define_vn:
    define_vn, pronunciation = translate_word(keyword)  # Dịch + lấy cách phát âm
else:
    _, pronunciation = translate_word(keyword)  # Chỉ lấy cách phát âm

print(f"📌 {keyword.capitalize()} /{pronunciation}/ ({word_type}): {define_vn}")

if subnet_dir:
    save_dir=save_dir+"//"+subnet_dir
filename = f"{keyword}.jpg"

# 🔹 Tạo thư mục lưu flashcards
os.makedirs(save_dir, exist_ok=True)

# 🔹 Tải ảnh từ Google
crawler = GoogleImageCrawler(storage={"root_dir": save_dir})
crawler.crawl(keyword=keyword, max_num=1)

# 🔹 Xử lý ảnh
file_list = os.listdir(save_dir)
if file_list:
    old_file = os.path.join(save_dir, file_list[0])
    new_file = os.path.join(save_dir, filename)

       # Đọc ảnh bằng OpenCV
    img_cv = cv2.imread(old_file)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)  # Chuyển sang RGB
    
    # Resize ảnh về 128x128
    img_cv = cv2.resize(img_cv, (128, 128))

    # 🔹 Chuyển sang HSV để phân tích màu
    img_hsv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2HSV)

    # Chuyển pixel sang định dạng HSV
    pixels_hsv = img_hsv.reshape((-1, 3))
    pixels_hsv = np.float32(pixels_hsv)

    # Áp dụng K-Means để tìm màu chủ đạo
    k = 3  # Chọn 3 màu chính
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, palette = cv2.kmeans(pixels_hsv, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

    # Chuyển sang RGB để sử dụng
    palette_rgb = [tuple(map(int, cv2.cvtColor(np.uint8([[c]]), cv2.COLOR_HSV2RGB)[0][0])) for c in palette]

    # 🔹 Loại bỏ màu tối, xám, nâu
    valid_colors = []
    for i, (h, s, v) in enumerate(palette):
        if v > 60 and s > 50:  # Loại màu tối & màu nhạt
            if not (h < 20 and s < 100 and v < 150):  # Loại màu nâu
                valid_colors.append((labels.flatten().tolist().count(i), palette_rgb[i]))

    # 🔹 Ưu tiên màu 7 sắc cầu vồng (Hue 0° - 300°)
    rainbow_colors = []
    for count, color in valid_colors:
        h, s, v = cv2.cvtColor(np.uint8([[color]]), cv2.COLOR_RGB2HSV)[0][0]
        if 0 <= h <= 300:
            rainbow_colors.append((count, color))

    # Chọn màu xuất hiện nhiều nhất trong danh sách hợp lệ
    chosen_colors = rainbow_colors if rainbow_colors else valid_colors
    dominant_color = chosen_colors[0][1] if chosen_colors else (0, 0, 255)
        # Chuyển ảnh sang PIL để vẽ flashcard
    img_pil = Image.fromarray(img_cv)

    # 🔹 Tạo flashcard với viền màu chủ đạo
    card_width, card_height = 200, 280
    flashcard = Image.new("RGB", (card_width, card_height), "white")

    draw = ImageDraw.Draw(flashcard)
    border_width = 4
    draw.rectangle(
        [(border_width, border_width), (card_width - border_width, card_height - border_width)], 
        outline=dominant_color, width=border_width
    )
    # Dán ảnh vào flashcard
    img_x = (card_width - 128) // 2
    img_y = 20
    flashcard.paste(img_pil, (img_x, img_y))

    # 🔹 Thêm chữ (Từ + Phiên âm + Loại từ + Nghĩa)
    font = ImageFont.truetype("arial.ttf", 20)
    font_type = ImageFont.truetype("arial.ttf", 16)
    font_vi = ImageFont.truetype("arial.ttf", 18)

    # Từ tiếng Anh
    text_x = (card_width - draw.textlength(keyword.capitalize(), font=font)) // 2
    draw.text((text_x, 160), keyword.capitalize(), fill=dominant_color, font=font)

    # Phiên âm
    text_x_pron = (card_width - draw.textlength(f"/{pronunciation}/", font=font_type)) // 2
    draw.text((text_x_pron, 185), f"/{pronunciation}/", fill="black", font=font_type)

    # Loại từ
    text_x_type = (card_width - draw.textlength(f"({word_type})", font=font_type)) // 2
    draw.text((text_x_type, 210), f"({word_type})", fill="gray", font=font_type)

    # Nghĩa tiếng Việt
    text_x_vi = (card_width - draw.textlength(define_vn.capitalize(), font=font_vi)) // 2
    draw.text((text_x_vi, 240), define_vn.capitalize(), fill="black", font=font_vi)

    # 🔹 Lưu flashcard
    flashcard.save(new_file)

    # Xóa file ảnh gốc
    os.remove(old_file)

print(f"🎴 Flashcard đã được tạo: {save_dir}/{filename}")
