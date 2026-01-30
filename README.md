> ⚠️ **Notice:** This project is for **Non-Commercial Use Only**.
Tommy Talent – Upute za Korištenje i Testiranje
Dobrodošli u testnu fazu aplikacije Tommy Talent. 
Ovaj dokument sadrži važne napomene o testnom okruženju, upute za svaku ulogu (Zaposlenik, Manager, HR) te scenarij za testiranje.

**⚠️ VAŽNA NAPOMENA ZA TESTERE (Obavezno pročitati!)**
Budući da se aplikacija vrti na testnom serveru (Cloud), vrijede sljedeća pravila:
1.	Privremena Baza: Baza podataka se resetira (briše) ako se aplikacija ne koristi dulje od 30 minuta ili ako se dogodi novo ažuriranje koda.
o	Što to znači? Podaci koje unesete danas možda neće biti tu sutra ujutro.
2.	Kako sačuvati rad?
o	Prije kraja testiranja, HR ili Admin moraju otići na tab "📥 Export Podataka" i preuzeti Excel datoteku. To je vaš jedini backup.
3.	Lozinke: Svi korisnici inicijalno imaju lozinku: user123. Molimo vas da je promijenite odmah pri prvoj prijavi.

**🔐 1. Prijava u sustav**
•	Web adresa: (Ovdje ćeš umetnuti link svoje aplikacije)
•	Korisničko ime: Vaš Kadrovski broj (npr. 100, 101, 500).
•	Lozinka: user123 (za prvu prijavu).
•	Admin pristup: admin / admin123

**🧪 2. Protokol za Testiranje ("Smoke Test")**
Molimo vas da prođete ovaj scenarij kako biste potvrdili ispravnost procesa:
Korak 1: Priprema (HR)
1.	Prijavite se kao HR (ili Admin).
2.	Uvezite Excel s testnim zaposlenicima (Format: ID | Ime | Pozicija | Odjel | ManagerID | Rola).
3.	Provjerite je li aktivan period (npr. "2025-Q1").
Korak 2: Postavljanje Ciljeva (Manager)
1.	Prijavite se kao Manager. Odaberite pogled "👔 Voditelj".
2.	Postavite 1 cilj svom zaposleniku (npr. "Povećanje prodaje", težina 100%).
Korak 3: Provjera (Zaposlenik)
1.	Prijavite se kao taj Zaposlenik.
2.	Idite na "Moji Ciljevi" – morate vidjeti cilj koji je Manager postavio.
3.	Idite na "Moj Profil" – promijenite lozinku.
Korak 4: Procjena - Skrivanje (Manager & Zaposlenik)
1.	Manager: Unesite ocjene za zaposlenika, napišite komentar, ali kliknite samo "Spremi kao Nacrt" (NE zaključavaj).
2.	Zaposlenik: Osvježite svoju stranicu "Moja Procjena". Morate vidjeti poruku "⚠️ Vaš voditelj trenutno radi na procjeni". Ne smijete vidjeti ocjene.
Korak 5: Finalizacija (Manager)
1.	Manager: Kliknite gumb "🔒 ZAKLJUČAJ I POŠALJI".
Korak 6: Konačni uvid (Zaposlenik)
1.	Zaposlenik: Osvježite stranicu. Sada morate vidjeti sve ocjene, grafove i komentar.

**👤 3. Upute za Zaposlenike (Employee)**
🏠 Moj Profil
•	Ovdje vidite svoje podatke i povijest razvoja.
•	Promjena lozinke: Kliknite na "🔐 Promjena Lozinke", unesite staru (user123) i novu lozinku.
🎯 Moji Ciljevi
•	Pregled ciljeva koje je postavio voditelj.
•	Klikom na strelicu pored cilja vidite detalje i KPI-jeve.
📝 Moja Procjena
•	Dok proces traje, vidite samo status "U tijeku".
•	Kada voditelj zaključa procjenu, vidite ocjene (1-5), 9-Box kategoriju i komentar.
🚀 Moj Razvoj (IDP)
•	Pregled vašeg razvojnog plana po modelu 70-20-10 (Učenje kroz rad, Učenje od drugih, Edukacija).

**👔 4. Upute za Voditelje (Manager)**
👀 Dva načina rada (Prekidač)
U lijevom izborniku imate opciju "Način pregleda":
1.	👔 Voditelj (Moj Tim): Za upravljanje vašim ljudima.
2.	👤 Zaposlenik (Moj Profil): Za pregled vaše vlastite procjene (ako imate nadređenog).
🎯 Postavljanje Ciljeva
•	Idite na "Moji Ciljevi" -> "Novi Cilj".
•	Pravilo: Ukupna težina ciljeva za jednog zaposlenika mora biti 100%.
📝 Unos Procjena
•	Otvorite karticu zaposlenika.
•	Ocijenite Učinak (KPI, Kvaliteta...) i Potencijal (Agilnost, Ambicija...).
•	Spremi kao nacrt: Možete mijenjati podatke koliko god želite.
•	Zaključaj i pošalji: Tek tada zaposlenik vidi rezultate. Ovo je nepovratno.
🚀 IDP (Razvojni plan)
•	Definirajte snage i područja za razvoj.
•	Ispunite tablice aktivnosti (70-20-10) i spremite plan.

**📊 5. Upute za HR i Admine**
🗂️ Upravljanje Korisnicima
•	Import: Koristite pripremljeni Excel predložak.
o	Stupci: A=ID, B=Ime, C=Pozicija, D=Odjel, E=ManagerID, F=Rola (Employee/Manager/HR).
•	Reset lozinke: Ako netko zaboravi lozinku, u tabu "Šifarnik" mu možete postaviti novu.
⚙️ Tehničko Održavanje (Backup)
•	Zbog prirode testnog servera, redovito radite Backup:
1.	Idite na Admin Panel -> Backup & Restore.
2.	Kliknite "💾 Napravi Backup Sada".
3.	Preuzmite datoteku na svoje računalo.
•	Ako se baza resetira, ovdje možete učitati tu datoteku ("Restore") i vratiti sve podatke.

**❓ Česta pitanja (FAQ)**
Q: Manager mi je unio ocjene, ali ništa ne vidim? A: Manager mora kliknuti crveni gumb "ZAKLJUČAJ I POŠALJI". Dok je procjena u statusu "Nacrt", ona je tajna.
Q: Zašto ne vidim Managere u popisu zaposlenika? A: Vjerojatno su kreirani samo kao korisnici (za login), ali nisu uneseni u Excel/Matičnu knjigu. HR ih treba dodati kroz "Dodaj novog zaposlenika" koristeći isti ID.
Q: Aplikacija javlja grešku nakon importa Excela. A: Provjerite ima li Excel praznih redova ili zaglavlja (npr. tekst "ID" u stupcu za broj). U Admin panelu postoji alat "Popravi Import" za brisanje takvih grešaka.
