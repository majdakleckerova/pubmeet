# PubMeet
### dodělat do pondělí
- ~~úprava profilu~~ (update do db usera) - už funguje i profilovka
- ~~odebrat nahrání profilovky při registraci~~
- ~~redirecty z registrace a loginu na profil~~
- ~~odhlášení~~

- **profily** :
    - ~~majda: seznam oblíbených hospod~~
    - ~~seznam přátel (+ zobrazit profil)~~
    - ~~majda: aktuální navštěvovaná hospoda (if friends)~~
    - ~~pole s profilem - přezdívka, bio, atd.~~
    - **majda: ?mini profilovky k přátelům + žádostem?**
    - ~~majda: u žádostí do přátel upravit @ a zobrazit profil~~
 
- **uživatelé**:
    - ~~zprovoznit zobrazit profil (vytvořit templates automaticky každému novému uživateli s polem s profilem + přátelé + fav hospody + přidat do přátel + aktuální lokace, když přátelé)~~
    - ~~?majda: logika kolem žádostí (poslat žádost/přijmout žádost/žádost odeslána/přátelé)~~

- **mapa**:
    - ~~david: hezčí markery (kulatý s fotkou hospody?)~~
    - ~~david: možná přidat něco do popupu adresu kurzívou~~
    - ~~david: zamčení mapy~~
    - ~~david?: ukázat current userovi aktuálně navštěvovanou hospodu~~
    - ~~david?: at když lajknu/navštěvuju hospodu a vyjedu z toho tak když se na to vrátim at se ukáže odebrat like/opustit~~
    - ~~návštěvníci hospody~~
    - ~~srovnat popupy~~
    - ~~david: zkusit opravit lajky a navštěvy~~
- **backend**:
    - ~~upravit žádosti o přátelství~~


### nasazení
- ~~hash, brat vse pres id uzivatele~~ - **omezený přístup do db, hashované heslo z právního hlediska stačí**
- ~~user po x hodinach automaticky opusti roomku~~ **(majda)**
- ~~přepis do php **(david)**~~
1. vytvořit mobilní rozhraní **(majda)**
2. vylepšit design je to shit **(majda)**
3. přidat další funkcionalitu (rozhraní hospod - ceník, události, otebíračka, pozvánky mezi users) **(majda, david)**
4. upravit zobrazování hlášek jako například "na váš mail byl zaslán verification link, po kliknutí bude vaše registrace dokončena" atd.
5. roztřídit kód (routy, endpointy) ... začíná v tom být zmatek
6. upravit kód před nasazením
7. Co zapomenuté heslo??? co s tim???

#### Rozhraní hospod
- vytvořit model app/models/pub.py ... měl by obsahovat název, souřadnice, adresa, otevírací doba, nápojový lístek, události
- vytvořit template hospody.html (swipovaci)
- vyplňování atributů hospod formou formuláře
- události - formulář: datum, čas od, čas do, název, poznámka + možnost usera dát zúčastnit se, pozvat někoho
- fotky hospod do swipovaciho templatu???
