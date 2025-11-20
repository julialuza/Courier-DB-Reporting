import mysql.connector
import matplotlib.pyplot as plt #do stworzenia wykresu
from reportlab.platypus import TableStyle, Image
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

load_dotenv()

#czcionka ktora obsluguje polskie znaki
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

#funkcja do polaczenia z bazą MySQL i pobierania danych
def fetch_data(query, params=None):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port = int(os.getenv("DB_PORT")),
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        database = os.getenv("DB_NAME"),
    )
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute(query, params)
        result = cursor.fetchall()
    conn.close()
    return result

#generowanie raportu z grupowaniem

def generate_grouped_report():
    today_date = datetime.today().strftime('%Y-%m-%d')

    date_style = ParagraphStyle(
        'DateStyle',
        fontName='DejaVuSans',
        fontSize=10,
        leading=16,
        alignment=2,
        spaceBefore=0,
        spaceAfter=10,
        backColor=HexColor("#20654E"),
        textColor=HexColor("#FFFFFF"),
    )

    #tworzenie napisu z dzisiejszą datą
    date_paragraph = Paragraph(f'Data: {today_date}', date_style)

    query = """
    SELECT imię, nazwisko, numer_tel, pensja, stanowisko
    FROM pracownik
    ORDER BY stanowisko, nazwisko, imię;
    """
    data = fetch_data(query)

    doc = SimpleDocTemplate("lista_pracownikow.pdf", pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    styles['Normal'].fontName = 'DejaVuSans'

    title_style = ParagraphStyle(
        'Title',
        fontName='DejaVuSans',
        fontSize=18,
        leading=24,
        alignment=1,  # Wyśrodkowanie
        spaceAfter=0,
        backColor=HexColor("#000000"),
        textColor=HexColor("#FFFFFF"),
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontName='DejaVuSans',
        fontSize=14,
        leading=22,
        alignment=1,  # Wyśrodkowanie
        spaceAfter=0,
        backColor=HexColor("#000000"),
        textColor=HexColor("#ABABAB"),
    )
    header_style = ParagraphStyle(
        'HeaderStyle',
        fontName='DejaVuSans',
        fontSize=12,
        leading=16,
        alignment=0,  # Do lewej
        spaceBefore=10,
        spaceAfter=5,
        textColor=HexColor("#20654E"),
    )

    #tytuł i podtytuł
    title = Paragraph("Lista pracowników", title_style)
    subtitle = Paragraph("według stanowisk", subtitle_style)

    elements.append(title)
    elements.append(subtitle)
    elements.append(date_paragraph)

    col_widths = [112, 112, 112, 112]  #szerokość kolumn w tabelce
    #grupowanie danych według stanowiska
    grouped_data = defaultdict(list)
    for row in data:
        grouped_data[row['stanowisko']].append(row)

    for stanowisko, rows in grouped_data.items():
        # Dodaj nagłówek dla stanowiska
        header = Paragraph(f"Stanowisko: {stanowisko}", header_style)
        elements.append(header)

        # Tworzenie tabeli dla stanowiska
        table_data = [["Imię", "Nazwisko", "Numer telefonu", "Pensja"]]
        table_data += [[row['imię'], row['nazwisko'], row['numer_tel'], row['pensja']] for row in rows]
        table = Table(table_data, colWidths=col_widths)
        style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(style)
        elements.append(table)
        elements.append(Spacer(1, 12))  # Odstęp między tabelami

    doc.build(elements)
    print("Raport z grupowaniem zapisano jako 'lista_pracownikow.pdf'.")


# Generowanie raportu z wykresem
def generate_chart_report(start_date,end_date):
    today_date = datetime.today().strftime('%Y-%m-%d')

    date_style = ParagraphStyle(
        'DateStyle',
        fontName='DejaVuSans',
        fontSize=10,
        leading=16,
        alignment=2,  # Wyśrodkowanie
        spaceBefore=0,
        spaceAfter=10,
        backColor=HexColor("#20654E"),
        textColor=HexColor("#FFFFFF"),
    )

    # Tworzenie napisu z dzisiejszą datą
    date_paragraph = Paragraph(f'Data: {today_date}', date_style)
    query = """
    SELECT 
        p.imię, 
        p.nazwisko, 
        p.pensja, 
        COUNT(rd.ID_przesyłki) AS liczba_dostaw
    FROM 
        pracownik p
    JOIN 
        kurier k ON k.ID_kuriera = p.ID_pracownika
    LEFT JOIN 
        realizacja_dostawy rd ON rd.ID_kuriera = k.ID_kuriera
    WHERE 
        rd.data_zakonczenia BETWEEN %s AND %s
    GROUP BY 
        p.ID_pracownika
    ORDER BY 
        liczba_dostaw DESC;
    """
    #start_date = input("Podaj datę początkową (YYYY-MM-DD): ")
    #end_date = input("Podaj datę końcową (YYYY-MM-DD): ")
    data = fetch_data(query, (start_date, end_date))

    # Tworzenie stylów dla tytułu i podtytułu
    title_style = ParagraphStyle(
        'Title',
        fontName='DejaVuSans',
        fontSize=18,
        leading=24,
        alignment=1,  # Wyśrodkowanie
        spaceAfter=0,
        backColor=HexColor("#000000"),
        textColor=HexColor("#FFFFFF")
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontName='DejaVuSans',
        fontSize=12,
        leading=22,
        alignment=1,  # Wyśrodkowanie
        spaceAfter=0,
        backColor=HexColor("#000000"),
        textColor=HexColor("#ABABAB"),
    )
    # Tytuł i podtytuł
    title = Paragraph("Liczba zrealizowanych dostaw przez kurierów", title_style)
    subtitle = Paragraph(f"w okresie: {start_date} - {end_date}", subtitle_style)

    # Tworzenie tabeli z wynikami
    table_data = [["Imię", "Nazwisko", "Pensja", "Liczba Dostaw"]]
    table_data += [
        [row['imię'], row['nazwisko'], row['pensja'], row['liczba_dostaw']] for row in data
    ]
    # Ustawienie proporcji szerokości kolumn
    col_widths = [125, 125, 100, 100]  # Kolumny imię, nazwisko, pensja, liczba dostaw
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Nagłówek tabeli
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Wyśrodkowanie
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Siatka tabeli
    ]))

    # Generowanie wykresu
    names = [f"{row['imię']} {row['nazwisko']}" for row in data]
    deliveries = [row['liczba_dostaw'] for row in data]
    plt.figure(figsize=(10, 6))
    plt.bar(names, deliveries, color='#20654E')
    plt.xlabel('Kurier')
    plt.ylabel('Liczba dostaw')
    plt.title('Liczba dostaw według pracowników')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('chart.png')
    plt.close()

    # Generowanie PDF
    doc = SimpleDocTemplate("liczba_dostaw.pdf", pagesize=letter)
    elements = [title, subtitle, date_paragraph, Spacer(1, 12), table, Spacer(1, 24)]  # Spacer przed wykresem

    # Dodanie wykresu do PDF
    img = Image("chart.png", width=500, height=300)
    elements.append(img)

    # Tworzenie dokumentu
    doc.build(elements)
    print("Raport z wykresem zapisano jako 'liczba_dostaw.pdf'.")

# Generowanie raportu w formie formularza
def generate_form_report(id_przesylki):
    today_date = datetime.today().strftime('%Y-%m-%d')

    date_style = ParagraphStyle(
        'DateStyle',
        fontName='DejaVuSans',
        fontSize=10,
        leading=16,
        alignment=2,  # Wyśrodkowanie
        spaceBefore=0,
        spaceAfter=10,
        backColor=HexColor("#20654E"),
        textColor=HexColor("#FFFFFF"),
    )

    # Tworzenie napisu z dzisiejszą datą
    date_paragraph = Paragraph(f'Data: {today_date}', date_style)
    # Pobranie danych
    #id_przesylki = input("Podaj ID przesyłki: ")
    query = """
        SELECT 
            p.ID_przesyłki, p.waga, p.rozmiar,
            n.imię AS nadawca_imie, n.nazwisko AS nadawca_nazwisko, n.ulica AS nadawca_ulica, 
            n.miasto AS nadawca_miasto, n.kod_pocztowy AS nadawca_kod_pocztowy, n.nr_tel AS nadawca_nr_tel,
            a.imię AS adresat_imie, a.nazwisko AS adresat_nazwisko, a.ulica AS adresat_ulica, 
            a.miasto AS adresat_miasto, a.kod_pocztowy AS adresat_kod_pocztowy, a.nr_tel AS adresat_nr_tel,
            sp.stan, os.lokalizacja_paczki, os.data_zmiany_stanu, 
            r.status_platnosci, r.forma_platnosci, r.data_wystawienia, r.kwota
        FROM 
            przesylka p
        JOIN 
            nadawca n ON p.ID_nadawcy = n.ID_nadawcy
        JOIN 
            adresat a ON p.ID_adresata = a.ID_adresata
        JOIN 
            opis_stanu_przesylki os ON p.ID_przesyłki = os.ID_przesyłki
        JOIN 
            stan_przesyłki sp ON os.ID_stanu = sp.ID_stanu
        LEFT JOIN 
            rachunek r ON p.ID_rachunku = r.ID_rachunku
        WHERE 
            p.ID_przesyłki = %s
            AND os.data_zmiany_stanu = (
                SELECT MAX(os2.data_zmiany_stanu)
                FROM opis_stanu_przesylki os2
                WHERE os2.ID_przesyłki = p.ID_przesyłki
            );
    """
    data = fetch_data(query, (id_przesylki,))

    if not data:
        print("Brak danych dla podanego ID przesyłki.")
        return

    # Styl tytułu i podtytułu
    title_style = ParagraphStyle(
        'Title',
        fontName='DejaVuSans',
        fontSize=18,
        leading=24,
        alignment=1,  # Wyśrodkowanie
        spaceAfter=0,
        backColor=HexColor("#000000"),
        textColor=HexColor("#FFFFFF")
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontName='DejaVuSans',
        fontSize=12,
        leading=22,
        alignment=1,  # Wyśrodkowanie
        spaceAfter=0,
        backColor=HexColor("#000000"),
        textColor=HexColor("#ABABAB"),
    )
    text_style = ParagraphStyle(
        'Text',
        fontName='DejaVuSans',
        fontSize=12,
        leading=14,
        spaceAfter=6
    )
    section_header_style = ParagraphStyle(
        'SectionHeader',
        fontName='DejaVuSans',
        fontSize=14,
        leading=18,
        spaceBefore=6,
        spaceAfter=6,
        backColor=HexColor("#323232"),
        textColor=HexColor("#FFFFFF")
    )

    # Generowanie PDF
    doc = SimpleDocTemplate("szczegoly_przesylki.pdf", pagesize=letter) #służy do tworzenia pdf
    elements = []
    elements.append(Paragraph("Przesyłka", title_style))
    elements.append(Paragraph("Zestawienie informacji o przesyłce", subtitle_style))
    elements.append(date_paragraph)
    elements.append(Spacer(1, 12))
    # Iteracja po wierszach danych
    for row in data:
        # Informacje o przesyłce
        elements.append(Paragraph("Szczegóły przesyłki", section_header_style))
        elements.append(Paragraph(f"ID przesyłki: {row['ID_przesyłki']}", text_style))
        elements.append(Paragraph(f"Waga: {row['waga']} kg", text_style))
        elements.append(Paragraph(f"Rozmiar: {row['rozmiar']}", text_style))
        elements.append(Spacer(1, 12))
        # Informacje o stanie przesyłki
        elements.append(Paragraph("Stan przesyłki", section_header_style))
        elements.append(Paragraph(f"Aktualny stan: {row['stan']}", text_style))
        elements.append(Paragraph(f"Lokalizacja: {row['lokalizacja_paczki']}", text_style))
        elements.append(Paragraph(f"Data ostatniej zmiany stanu: {row['data_zmiany_stanu']}", text_style))
        elements.append(Spacer(1, 12))
        # Informacje o nadawcy
        elements.append(Paragraph("Nadawca", section_header_style))
        elements.append(Paragraph(f"Imię i nazwisko: {row['nadawca_imie']} {row['nadawca_nazwisko']}", text_style))
        elements.append(Paragraph(f"Adres: {row['nadawca_ulica']}, {row['nadawca_miasto']}, {row['nadawca_kod_pocztowy']}", text_style))
        elements.append(Paragraph(f"Numer telefonu: {row['nadawca_nr_tel']}", text_style))
        elements.append(Spacer(1, 12))
        # Informacje o adresacie
        elements.append(Paragraph("Adresat", section_header_style))
        elements.append(Paragraph(f"Imię i nazwisko: {row['adresat_imie']} {row['adresat_nazwisko']}", text_style))
        elements.append(Paragraph(f"Adres: {row['adresat_ulica']}, {row['adresat_miasto']}, {row['adresat_kod_pocztowy']}", text_style))
        elements.append(Paragraph(f"Numer telefonu: {row['adresat_nr_tel']}", text_style))
        elements.append(Spacer(1, 12))
        # Informacje o rachunku
        if row['status_platnosci']:
            elements.append(Paragraph("Rachunek", section_header_style))
            elements.append(Paragraph(f"Status płatności: {row['status_platnosci']}", text_style))
            elements.append(Paragraph(f"Kwota: {row['kwota']} PLN", text_style))
            elements.append(Paragraph(f"Data wystawienia: {row['data_wystawienia']}", text_style))

    doc.build(elements)
    print("Raport zapisano jako 'szczegoly_przesylki.pdf'.")

def main():
    if len(sys.argv) < 2:
        print("Brak argumentu określającego typ raportu. Wybierz 1, 2 lub 3.")
        return

    choice = sys.argv[1]  # Typ raportu
    if choice == "1":  # Raport z grupowaniem
        generate_grouped_report()
    elif choice == "2":  # Raport z wykresem
        if len(sys.argv) < 4:  # Sprawdź, czy są przekazane daty
            print("Brak wymaganych parametrów (start_date, end_date) dla raportu z wykresem.")
            return
        start_date = sys.argv[2]
        end_date = sys.argv[3]
        generate_chart_report(start_date, end_date)
    elif choice == "3":  # Raport w formie formularza
        if len(sys.argv) < 3:  #sprawdzenie, czy jest przekazane ID przesyłki
            print("Brak wymaganego parametru (id_przesylki) dla raportu w formie formularza.")
            return
        id_przesylki = sys.argv[2]
        generate_form_report(id_przesylki)
    else:
        print("Nieprawidłowy wybór. Wybierz 1, 2 lub 3.")

if __name__ == "__main__":
    main()
