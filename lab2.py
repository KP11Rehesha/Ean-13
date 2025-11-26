import tkinter as tk
from tkinter import messagebox
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
        sum_odd = sum(int(code_12[i]) for i in range(0, 12, 2))  # Позиції 1, 3...
        sum_even = sum(int(code_12[i]) for i in range(1, 12, 2))  # Позиції 2, 4...
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
            digit = int(d)
            if pattern[i] == 'L':
                binary += self.L_CODES[digit]
            else:
                binary += self.G_CODES[digit]
        binary += "01010"
        for d in right_part:
            binary += self.R_CODES[int(d)]
        binary += "101"


        module_w = 3
        h = 100
        quiet = 30

        img_w = (len(binary) * module_w) + (2 * quiet)
        img = Image.new('RGB', (img_w, h + 50), 'white')  # +50 пікселів знизу для тексту
        draw = ImageDraw.Draw(img)


        try:

            font = ImageFont.truetype("arial.ttf", 22)
        except IOError:
            font = ImageFont.load_default()


        x = quiet
        for bit in binary:
            if bit == '1':

                draw.rectangle([x, 10, x + module_w - 1, h], fill='black')
            x += module_w


        draw.text((quiet - 20, h + 10), full_code[0], fill='black', font=font)


        left_x = quiet + (3 * module_w) + 10
        formatted_left = f"{full_code[1]} {full_code[2]} {full_code[3]} {full_code[4]} {full_code[5]} {full_code[6]}"

        draw.text((left_x, h + 10), full_code[1:7], fill='black', font=font)


        right_x = quiet + (50 * module_w) + 10
        draw.text((right_x, h + 10), full_code[7:], fill='black', font=font)

        return img, full_code



def on_create_click():

    p_name = entry_name.get()
    p_code = entry_code.get()


    if not p_name:
        messagebox.showwarning("Увага", "Введіть назву товару!")
        return
    if len(p_code) != 12 or not p_code.isdigit():
        messagebox.showerror("Помилка", "Код має складатися з 12 цифр (0-9).")
        return

    try:

        generator = EAN13ManualGenerator()
        img, final_code = generator.generate_image(p_code)


        img_tk = ImageTk.PhotoImage(img)
        lbl_barcode_img.config(image=img_tk)
        lbl_barcode_img.image = img_tk


        lbl_status.config(text=f"Успішно закодовано: {p_name}\nПовний код: {final_code}", fg="green")

        #  PostgreSQL
        print(f"Готово до запису в БД: {p_name} - {final_code}")

    except Exception as e:
        messagebox.showerror("Помилка генерації", str(e))



root = tk.Tk()
root.title("Лаб: Кодування EAN-13")
root.geometry("400x500")


frame_input = tk.LabelFrame(root, text="Введення інформації", padx=10, pady=10)
frame_input.pack(padx=10, pady=10, fill="x")

tk.Label(frame_input, text="Назва товару:").pack(anchor="w")
entry_name = tk.Entry(frame_input)
entry_name.pack(fill="x", pady=5)

tk.Label(frame_input, text="Код (перші 12 цифр):").pack(anchor="w")
entry_code = tk.Entry(frame_input)
entry_code.pack(fill="x", pady=5)
tk.Label(frame_input, text="* 13-та цифра буде розрахована автоматично", font=("Arial", 8), fg="gray").pack(anchor="w")


btn_encode = tk.Button(root, text="Кодувати (Створити ШК)", command=on_create_click, bg="#e1f5fe", height=2)
btn_encode.pack(pady=10, fill="x", padx=10)


frame_output = tk.LabelFrame(root, text="Результат кодування", padx=10, pady=10)
frame_output.pack(padx=10, pady=10, fill="both", expand=True)

lbl_status = tk.Label(frame_output, text="Введіть дані та натисніть кнопку", fg="gray")
lbl_status.pack(pady=5)

lbl_barcode_img = tk.Label(frame_output)
lbl_barcode_img.pack(pady=10)

root.mainloop()