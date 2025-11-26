import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont



class EAN13ManualGenerator:
    def __init__(self):
        self.L_CODES = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011",
                        "0110111", "0001011"]
        self.G_CODES = ["0100111", "0110011", "0011011", "0100001", "0011101", "0111001", "0000101", "0010001",
                        "0001001", "0010111"]
        self.R_CODES = ["1110010", "1100110", "1101100", "1000010", "1011100", "1001110", "1010000", "1000100",
                        "1001000", "1110100"]
        self.PARITY_PATTERNS = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG",
                                "LGLGGL", "LGGLGL"]

    def calculate_check_digit(self, code_12):
        sum_odd = sum(int(code_12[i]) for i in range(0, 12, 2))
        sum_even = sum(int(code_12[i]) for i in range(1, 12, 2))
        total = sum_odd + (sum_even * 3)
        remainder = total % 10
        return 0 if remainder == 0 else 10 - remainder

    def generate_image(self, code_input):
        if len(code_input) != 12 or not code_input.isdigit():
            raise ValueError("Код має містити рівно 12 цифр!")

        check_digit = self.calculate_check_digit(code_input)
        full_code = code_input + str(check_digit)

        first_digit = int(full_code[0])
        left_part = full_code[1:7]
        right_part = full_code[7:13]
        pattern = self.PARITY_PATTERNS[first_digit]

        binary = "101"
        for i, d in enumerate(left_part):
            binary += self.L_CODES[int(d)] if pattern[i] == 'L' else self.G_CODES[int(d)]
        binary += "01010"
        for d in right_part:
            binary += self.R_CODES[int(d)]
        binary += "101"

        module_w = 3
        h = 100
        quiet = 30
        img_w = (len(binary) * module_w) + (2 * quiet)
        img = Image.new('RGB', (img_w, h + 50), 'white')
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 22)
        except:
            font = ImageFont.load_default()

        x = quiet
        for bit in binary:
            if bit == '1':
                draw.rectangle([x, 10, x + module_w - 1, h], fill='black')
            x += module_w

        draw.text((quiet - 20, h + 10), full_code[0], fill='black', font=font)
        draw.text((quiet + (3 * module_w) + 10, h + 10), full_code[1:7], fill='black', font=font)
        draw.text((quiet + (50 * module_w) + 10, h + 10), full_code[7:], fill='black', font=font)

        return img, full_code



class EAN13ManualDecoder:
    def __init__(self):

        gen = EAN13ManualGenerator()
        self.decode_L = {code: str(i) for i, code in enumerate(gen.L_CODES)}
        self.decode_G = {code: str(i) for i, code in enumerate(gen.G_CODES)}
        self.decode_R = {code: str(i) for i, code in enumerate(gen.R_CODES)}


        self.decode_parity = {pattern: str(i) for i, pattern in enumerate(gen.PARITY_PATTERNS)}

    def decode_image_file(self, filepath):

        img = Image.open(filepath).convert('L')  # Конвертуємо в Ч/Б
        width, height = img.size
        pixels = img.load()


        mid_y = height // 2
        row_bits = []


        raw_scan = [1 if pixels[x, mid_y] < 128 else 0 for x in range(width)]


        try:
            start_idx = raw_scan.index(1)
            end_idx = len(raw_scan) - 1 - raw_scan[::-1].index(1)
        except ValueError:
            raise ValueError("Штрих-код не знайдено (немає чорних пікселів)")

        barcode_pixel_width = end_idx - start_idx + 1  # +1 бо включно


        module_size = barcode_pixel_width / 95.0


        binary_string = ""
        for i in range(95):

            sample_x = start_idx + (i * module_size) + (module_size / 2)
            pixel_val = pixels[int(sample_x), mid_y]
            bit = '1' if pixel_val < 128 else '0'
            binary_string += bit

        if binary_string[:3] != "101" or binary_string[-3:] != "101":
            raise ValueError("Невірні маркери старту/стопу. Можливо зображення нечітке.")

        left_binary = binary_string[3:45]
        right_binary = binary_string[50:92]


        left_digits = ""
        parity_pattern = ""

        for i in range(0, 42, 7):
            chunk = left_binary[i:i + 7]
            if chunk in self.decode_L:
                left_digits += self.decode_L[chunk]
                parity_pattern += "L"
            elif chunk in self.decode_G:
                left_digits += self.decode_G[chunk]
                parity_pattern += "G"
            else:
                raise ValueError(f"Невідомий код лівої частини: {chunk}")


        right_digits = ""
        for i in range(0, 42, 7):
            chunk = right_binary[i:i + 7]
            if chunk in self.decode_R:
                right_digits += self.decode_R[chunk]
            else:
                raise ValueError(f"Невідомий код правої частини: {chunk}")


        if parity_pattern in self.decode_parity:
            first_digit = self.decode_parity[parity_pattern]
        else:
            first_digit = "?"

        full_code = first_digit + left_digits + right_digits
        return full_code



root = tk.Tk()
root.title("Лаб: Генератор та Декодер EAN-13")
root.geometry("500x700")


frame_gen = tk.LabelFrame(root, text="1. Генерація штрих-коду", padx=10, pady=10)
frame_gen.pack(padx=10, pady=5, fill="x")

tk.Label(frame_gen, text="Назва:").pack(anchor="w")
entry_name = tk.Entry(frame_gen)
entry_name.pack(fill="x")

tk.Label(frame_gen, text="12 цифр:").pack(anchor="w")
entry_code = tk.Entry(frame_gen)
entry_code.pack(fill="x")

lbl_img_preview = tk.Label(frame_gen)
lbl_img_preview.pack(pady=5)


def on_gen():
    try:
        gen = EAN13ManualGenerator()
        code = entry_code.get()
        if not code: return
        img, full_code = gen.generate_image(code)


        img_tk = ImageTk.PhotoImage(img)
        lbl_img_preview.config(image=img_tk)
        lbl_img_preview.image = img_tk


        img.save("temp_barcode.png")
        messagebox.showinfo("Успіх", f"Згенеровано код: {full_code}\nЗбережено як temp_barcode.png")
    except Exception as e:
        messagebox.showerror("Помилка", str(e))


tk.Button(frame_gen, text="Створити", command=on_gen, bg="#dddddd").pack(pady=5, fill="x")


frame_dec = tk.LabelFrame(root, text="2. Декодування (Зворотня дія)", padx=10, pady=10)
frame_dec.pack(padx=10, pady=5, fill="x")

lbl_decode_res = tk.Label(frame_dec, text="Оберіть файл для декодування", font=("Arial", 12))
lbl_decode_res.pack(pady=10)


def on_decode():
    filepath = filedialog.askopenfilename(filetypes=[("PNG Images", "*.png")])
    if not filepath: return

    try:
        decoder = EAN13ManualDecoder()
        result_code = decoder.decode_image_file(filepath)

        lbl_decode_res.config(text=f"Розпізнано код:\n{result_code}", fg="green", font=("Arial", 14, "bold"))
    except Exception as e:
        lbl_decode_res.config(text=f"Помилка: {e}", fg="red", font=("Arial", 10))


tk.Button(frame_dec, text="Завантажити зображення і Декодувати", command=on_decode, bg="#e1f5fe").pack(fill="x")

root.mainloop()