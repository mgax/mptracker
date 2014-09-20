revision = '5927719682b'
down_revision = '10e5732ecd4'

import uuid
from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.dialects import postgresql


def random_uuid():
    return str(uuid.uuid4())


def upgrade():
    op.create_table(
        'text',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('ns', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'text_version',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('text_id', postgresql.UUID(), nullable=False),
        sa.Column('time', sa.DateTime(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('more_content', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['text_id'], ['text.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    text_data = {
        'donations': (TEXT_DONATIONS, ""),
        'editorial': (TEXT_EDITORIAL, TEXT_EDITORIAL_MORE),
        'export': (TEXT_EXPORT, ""),
        'local': (TEXT_LOCAL, TEXT_LOCAL_MORE),
        'migrations': (TEXT_MIGRATIONS, ""),
        'policy': (TEXT_POLICY, TEXT_POLICY_MORE),
        'proposal_controversy': (TEXT_PROPOSAL_CONTROVERSY, ""),
        'social': (TEXT_SOCIAL, ""),
        'voting_controversy': (
            TEXT_VOTING_CONTROVERSY,
            TEXT_VOTING_CONTROVERSY_MORE,
        ),
    }

    text = sql.table( 'text',
        sql.column('id'),
        sql.column('ns'),
        sql.column('name'),
    )
    text_version = sql.table( 'text_version',
        sql.column('id'),
        sql.column('text_id'),
        sql.column('time'),
        sql.column('content'),
        sql.column('more_content'),
    )
    time = datetime(2014, 9, 20, 9, 6, 25)
    for name, (content, more_content) in text_data.items():
        text_id = random_uuid()
        op.execute(text.insert().values({
            'id': text_id,
            'ns': 'general',
            'name': name,
        }))
        op.execute(text_version.insert().values({
            'id': random_uuid(),
            'text_id': text_id,
            'time': time,
            'content': content,
            'more_content': more_content,
        }))



def downgrade():
    op.drop_table('text_version')
    op.drop_table('text')


TEXT_DONATIONS = """\
<h2>Ajută la dezvoltarea proiectului OpenParlament</h2>

<p>OpenParlament este un proiect independent, non-profit al Fundației Median Research Centre și al OpenPolitics.ro. Întreținerea platformei precum și dezvoltarea altor funcții complementare necesită noi resurse, de aceea orice donație este binevenită.</p>

<p>Ne poți ajuta donând orice sumă în unul din conturile de mai jos:</p>

<p>
  Fundația "MRC - Median Research Centre",<br>
  Raiffeisen Bank SA:<br>
  RO93 RZBR 0000 0600 1633 8757 (lei)<br>
  RO06 RZBR 0000 0600 1633 8771 (€)<br>
  RO65 RZBR 0000 0600 1633 8776 ($)<br>
  S.W.I.F.T.: RZBRROBU
</p>

<p>
  Pentru orice alt fel de ajutor scrie-ne.<br>
  Mulțumim pentru sprijin!
</p>

<p>Echipa OpenParlament</p>
"""


TEXT_EDITORIAL = """\
<h2>De ce este necesar OpenParlament?</h2>

<p>Pentru mulți dintre români Parlamentul este o instituție bugetofagă, populată de traseiști, penali și chiulangii. Această atitudine de respingere in corpore contribuie la perpetuarea stiuației actuale în care politica este hiper-personalizată, dominată de teme simbolice și de acuzații mutuale de corupție.
</p>
"""


TEXT_EDITORIAL_MORE = """\
<p>În același timp, o majoritate a cetățenilor știe foarte puține despre procesul legislativ, despre ce fac grupurile parlamentare, dar și despre activitatea individuală a parlamentarilor - fie că e vorba de specializare în anumite politici, fie că vorbim de reprezentarea intereselor locuitorilor din circumscripțiile și colegiile lor.</p>

<p>OpenParlament este un proiect non-guvernamental, non-profit al Fundației Median Research Centre și al OpenPolitics.ro ce răspunde direct acestei probleme, prezentând în mod accesibil și ușor de înțeles informații despre toate aceste aspect. Astfel, OpenParlament este un efort de a deschide cutia neagră a reprezentării politice din România, ce se concentrează pe trei dimensiuni: activitatea individuală a deputaților, procesul legislativ și funcționarea grupurilor parlamentare.</p>


<p>Informațiile prezentate de aplicație pot fi folosite de jurnaliști, activiști sau simplii cetățeni. Astfel, unul dintre scopurile proiectului este de a crește nivelul de cunoștințe și înțelegere al cetățenilor cu privire la activitatea partidelor parlamentare și a deputaților, sporind astfel, pe termen lung, șansele responsabilizării aleșilor și ale unei decizii de vot informate. Un alt scop este de a facilita monitorizarea procesului legislativ pe subiecte majore de politici publice de către cetățenii și organizații non-guvernamentale interesate.</p>

<p>În plus, prin intermediul aplicației, jurnaliștii au acces direct la toate legile adoptate tacit în Parlament, la cele mai recente schimbări de afiliere politică, precum și la inițiativele legislative controversate și voturile controversate din Camera Deputaților.</p>

<p>OpenParlament se concentrează asupra Camerei Deputaților în principal din cauza absenței votului electronic de la Senat pentru cea mai mare parte a anului 2013. În măsura obținerii resurselor necesare, vom încerca lansarea unei aplicații identice pentru Senat și senatori. În momentul de față, aplicația prezintă informații referitoare la procesul legislativ din Senat doar în cazul traseului urmat de propunerile legislative și proiecte de lege.</p>

<p>Actualizarea datelor preluate de pe situl Camerei Deputaților se face la fiecare două zile. Alte date au fost preluate de pe situl Autorității Electorale Permanente respectiv din proiectul Verifică Integritatea al României Curate. În rândurile următoare vom prezenta și explica succint principalele funcții ale aplicației.</p>

<h3>Fii la curent cu schimbarile legislative și politice controversate!</h3>

<p>Secțiunea legi controversate permite monitorizarea procesului legislativ al unor propuneri și proiecte de lege, inițiate în această legislatură, care au fost considerate problematice de către media, organizații non-guvernamentale sau experții Median Research Centre. Fiecare propunere legislativă din această secțiune este însoțită de detalii asupra controversei stârnite și de link-uri către articolele din media sau luările de poziție ale organizațiilor non-guvernamentale referitoare la aceasta.</p>

<p>Secțiunea voturi controversate prezintă și explică votul fiecărui deputat asupra unor proiecte de lege și propuneri legislative inițiate în această legislatură sau în precedentele, care au fost considerate problematice de către media, organizații non-guvernamentale sau experții Median Research Centre. Lista legilor și voturilor controversate va fi actualizată periodic, folosind, sperăm, și contribuția dumneavoastră, a utilizatorilor.</p>

<p>Adoptarea tacită a legilor în prima cameră sesizată ridică întrebări asupra calității procesului legislativ și poate contribui la decredibilizarea Parlamentului. Secțiunea dedicată legilor adoptate tacit cuprinde lista tuturor propunerilor și proiectelor de lege adoptate în acest fel precum și toate informațiile asupra parcursului acestora în Parlament. De asemenea, secțiunea include date asupra magnitudinii fenomenului de la introducerea procedurii și până în prezent precum și explicații asupra cauzelor și implicațiilor acestuia.</p>

<p>Aplicația permite vizualizarea celor mai recente schimbări de afiliere ale deputaților. Desigur, există o întârziere între momentul în care deputatul face cererea de schimbare a afilierii și momentul în care aceasta devine efectivă prin citirea în plen a anunțului afilierii la un alt grup parlamentar și este consemnată pe situl oficial al Camerei Deputaților. Legat de acest aspect, aplicația calculează și loialitatea la vot a fiecărui deputat față de guvern tocmai pentru a identifica posibilele cazuri în care deputați din opoziție sprijină guvernul și majoritatea parlamentară fără a schimba în mod formal grupul politic din care fac parte.</p>

<h3>Urmărește evoluțiile legislative din 15 domenii de politici publice!</h3>

<p>OpenParlament pune la dispoziția organizațiilor non-guvernamentale și cetățenilor interesați, într-un mod ușor de înțeles și utilizat, informații ce permit urmărirea și monitorizarea procesului legislativ pe 15 domenii de politici publice:</p>

<ul>
  <li>Administrație publică și mediu,
  <li>Agricultură,
  <li>Apărare și securitate,
  <li>Cultură,
  <li>Drepturile omului,
  <li>Economie,
  <li>Educație, tineret și sport,
  <li>Externe
  <li>Finanțe
  <li>Interne
  <li>Muncă
  <li>Sănătate
  <li>Tehnologia informației
  <li>Transporturi
  <li>Uniunea Europeană
</ul>

<p>Toate inițiativele legislative și întrebările parlamentare din aceste domenii sunt incluse în categoria corespunzătoare utilizând două tipuri de informații. Pentru inițiativele legislative domeniul este stabilit prin analizarea comisiei parlamentare permanente la care Biroul permanent a trimis propunerea de lege pentru examinare. Conform Regulamentului Camerei Deputaților, Biroul permanent sesizează comisia permanentă "în competenţa căreia intră materia reglementată prin proiectul sau propunerea respectivă." (Art. 62, p. 23). Pentru întrebarile și interpelările parlamentare domeniul de politici publice este stabilit prin analizarea ministerului căreia îi sunt adresate acestea. Compatibilitatea celor două tipuri de indicatori este asigurată de paralelismul dintre jurisdicția comisiilor parlamentare permanente și cea a ministerelor în sistemul parlamentar românesc.</p>

<p>Pe baza acestor indicatori aplicația oferă utilizatorilor și posibilitatea de a evalua specializarea deputaților români în cele 15 politici publice. Această funcție este realizată prin calcularea procentului de propuneri legislative, întrebări și interpelări parlamentare ale deputatului care corespund fiecărei politici publice și prezentarea celor mai frecvente categorii.</p>

<h3>Monitorizează-ți deputatul!</h3>

<p>Această secțiune este formată din subpagini dedicate fiecărui deputat. Utilizatorii pot identifica deputatul care îi reprezintă sau de care sunt interesați căutând după nume, adresă, domeniu de politici publici (de care deputatul se preocupă cel mai mult) sau contracte cu statul.</p>

<p>Fiecare pagină de deputat cuprinde informații despre afilierea politică, comisiile parlamentare din care face sau a făcut parte deputatul, experiența parlamentară, declarația de avere din prima sesiune a actualei legislaturi precum și eventuale probleme de integritate.</p>

<p>Prezentăm, de asemenea, informații statistice asupra activității individuale: prezența la vot, gradul de loialitate față de propriul grup parlamentar și față de guvern, numărul de luări de cuvânt, inițiative legislative (total, respectiv numărul celor devenite legi), numărul de întrebări și interpelări parlamentare (total și legate de probleme din județul său). Toate acestea sunt însoțite de documentul respectiv sau de informații asupra poziției partidului, respectiv a guvernului în cazul fiecărui vot final.</p>

<p>Utilizatorii pot compara activitatea fiecărui deputat cu a altui deputat (folosind o serie de criterii prestabilite explicate mai jos) precum și similaritatea la vot cu toți membrii Camerei. Subpaginile deputaților includ ilustrații grafice ale frecvenței activităților parlamentare (timeline) respectiv ale conținutului acestora (word cloud bazat pe cuvintele care apar cel mai frecvent în inițiativele legislative și întrebările și interpelările parlamentare depuse de către aceștia).</p>

<p>Pagina fiecărui deputat conține și informații de contact precum: adresa biroului parlamentar, adrese oficiale de email, blog și sit personal, precum și adresele conturilor de media sociale (Facebook și Twitter) acolo unde acestea există.</p>

<p>Numerele asociate activității deputaților nu trebuie fetișizate. Acestea sunt indicatori ai implicării deputatului în activitatea de legiferare, deliberare, control parlamentar sau reprezentare a intereselor locale. Însă factori precum statutul și responsabilitățile deputatului în cadrul partidului, Camerei, guvernului, experiența și influența sa parlamentară ori apartenența la majoritatea parlamentară afectază atât oportunitățile de implicare în aceste activități cât și gradul lor de eficiență. Tocmai de aceea funcția de comparare a activității deputaților poate fi utilizată doar pe baza unor criterii prestabilite. Astfel, pot fi comparați doar deputați cu același număr de mandate parlamentare, cu funcții similare (ex.: președinte de comisie parlamentară, membru al biroului permanent etc), deputați din același județ sau din același grup parlamentar.</p>

<p>Totodată, există un număr de limitări inerente reutilizării datelor oficiale oferite de către situl Camerei Deputaților. Pe de o parte, media și organizații non-guvernamentale au observat că numărul de deputați prezenți la ședințe este uneori mai mic decât cel declarat în rapoartele oficiale ale comisiile parlamentare. Pe de altă parte, OpenParlament nu conține informații despre munca din teritoriu (ex.: audiențe din colegiu) a deputaților sau despre numărul de intervenții pe care aceștia le au în cadrul dezbaterilor din comisii. Am dori să includem aceste informații în viitor, dar pentru aceasta este nevoie de cooperarea deputaților, respectiv ca rapoartele comisiilor parlamentare să consemneze consecvent și constant intervențiile fiecărui membru al comisiei.</p>

<h3>Înțelege funcționarea grupurilor parlamentare!</h3>

<p>Informațiile privind specializarea în politici publice a fiecărui deputat membru al grupului parlamentar sunt agregate automat tot timpul astfel încât să oferim o imagine fidelă a nivelului de preocupare al grupului parlamentar respectiv față de subiectele analizate.</p>

<p>Aplicația indică nivelul mediu de loialitate la vot al tuturor membrilor, dar și al diverselor categorii de membrii (miniștrii, membrii ai biroului permanent, deputați aflați la primul mandat sau cu mai mult de un mandat) față de grupul parlamentar. De asemenea, calculăm și prezentăm în timp real nivelul mediu de loialitate la vot față de guvern al tuturor membrilor grupului.</p>

<p>Pagina grupului parlamentar conține informații și despre numărul total de întrebări și interpelări parlamentare, respectiv asupra procentului acestora care se referă la probleme locale din județele deputaților grupului.</p>

<h3>Descarcă datele și donează!</h3>

<p>Secțiunea export date permite descărcarea datelor asupra migrației parlamentare, a tuturor voturilor, întrebărilor și interpelărilor parlamentare în format csv. Toate datele din aplicația sunt distribuite sub licență CC BY 4.0. Aceasta implică necesitatea de a credita OpenParlament, de exemplu printr-un link, dacă folosiți datele. De asemenea, orice aplicații rezultate din această utilizare trebuie să fie distribuite folosind o licență de date deschise compatibilă.</p>

<p>Proiectul a fost realizat cu sprijinul financiar al Open Society Foundations. Întreținerea precum și dezvoltarea unor funcții complementare necesită noi resurse, de aceea orice donație este binevenită.</p>
"""


TEXT_EXPORT = """\
<p>Secțiunea export date permite descărcarea datelor asupra migrației parlamentare, a tuturor voturilor, întrebărilor și interpelărilor parlamentare în format csv. Toate datele din aplicația sunt distribuite sub licență CC BY 4.0. Aceasta implică necesitatea de a credita OpenParlament, de exemplu printr-un link, dacă folosiți datele. De asemenea, orice aplicații rezultate din această utilizare trebuie să fie distribuite folosind o licență de date deschise compatibilă.</p>

<p>Pentru lucrări academice citarea datelor este recomandată folosind referințele:</p>

<p>Popescu, Marina și Chiru, Mihail. 2014. The parliamentary votes of the Romanian Deputies. Machine readable data file, available at: http://website.firenze.grep.ro/export</p>

<p>Popescu, Marina și Chiru, Mihail. 2014. The parliamentary questions and interpellations of the Romanian Deputies. Machine readable data file, available at: http://website.firenze.grep.ro/export</p>

<p>Popescu, Marina și Chiru, Mihail. 2014. The party switching in the Romanian Chamber of Deputies. Machine readable data file, available at: http://website.firenze.grep.ro/export</p>
"""


TEXT_LOCAL = """\
<h2>Reprezentarea intereselor locale în Camera Deputaților</h2>

<p>
Pentru prima dată în România o aplicație online permite cetățenilor să evalueze nivelul de implicare al deputaților în reprezentarea intereselor locale (ceea ce literatura de specialitate numește "constituency service"). Aplicația face acest lucru folosind întrebările și interpelările parlamentare, care reprezintă conform studiilor legislative (Martin 2011; Russo 2011) unul dintre cei mai relevanți indicatori pentru măsurarea acestui tip de reprezentare politică.
</p>
"""


TEXT_LOCAL_MORE = """\
<p>
Echipa Open Parlament a creat un soft care analizează conținutul întrebărilor și interpelărilor parlamentare pentru a descoperi dacă acestea se referă la probleme locale, petiții sau memorii din județul deputatului. Soft-ul compară textele cu baze de date ce conțin toponime din județul deputatului, respectiv o serie de cuvinte-cheie relevante pentru acest tip de reprezentare și oferă un scor pe baza numărului de asocieri descoperite.
</p>

<p>
Rezultatul analizei automate de conținut a fost verificat prin codarea manuală a unui eșantion de aproximativ 11.000 de întrebări și interpelări. Aceasta a relevat un grad foarte ridicat de categorizare corectă. Erorile pot apărea, totuși, in principal din cauza calității grafice a pdf-urile scanate urcate pe situl oficial al Camerei Deputaților, pe care le convertim prin recunoaștere optică de caractere (OCR) înainte de analiza automată.
</p>

<p>
Sperăm în introducerea cât mai rapidă a semnăturilor digitale în locul tradiționalelor semnături și ștampile de înregistrare.
</p>

<h3>De ce e importantă urmărirea întrebărilor și interpelărilor pe teme locale?</h3>

<p>
Pe de o parte pentru că deputații investesc tot mai mult timp în această activitate. Figura 1 de mai jos prezintă evoluția numărului total de întrebări și interpelări din 1992, respectiv a celor cu teme locale din 1998, primul anul pentru care sunt disponibile copii electronice ale documentelor, până în 2013.
</p>

<figure>
  <img src="/static/help-figures/local1.jpeg">
  <figcaption>Figura 1: Evoluția întrebărilor și interpelarilor parlamentare pe teme locale</figcaption>
</figure>


<p>
În ciuda variațiilor anuale semnificative se poate observa un trend ascendent: tot mai multe întrebări si interpelări parlamentare adresează probleme din județele deputaților. Fenomenul este reprezentativ pentru creșterea importanței temelor locale în politica românească și a fost amplificat de schimbarea sistemului electoral, care a înlocuit votul pe liste închise cu un sistem mixt în care toți deputații sunt aleși în colegii uninominale. O analiză longitudinală multivariată folosind eșantioane de deputați aleși înainte și după schimbarea de sistem electoral, ce au fost ajustate prin algoritme de matching genetic, a indicat că după reforma electorală parlamentarii români inițiază de aproximativ 2 ori mai multe întrebări bazate pe petiții ale cetățenilor din județul lor, respectiv de 1.7 ori mai multe întrebări legate de infrastructura locală (Chiru 2014).
</p>

<p>
Această evoluție poate fi considerată îmbucurătoare în măsura în care indică o legătură mai strânsă între alegători, actori privați, autorități și instituții locale pe de o parte și reprezentatul lor în Parlament, pe de altă parte. Poate că demersurile unui deputat pentru deblocarea fondurilor necesare reparării unui drum județean nu vor avea efectul scontat în ministerul de resort sau vor trece neobservate în circumscripția respectivă, dar ne putem imagina că o orientare constantă către soluționarea unor probleme locale poate spori pe termen lung calitatea reprezentării individuale.
</p>

<p>
Desigur, unele dintre aceste întrebări locale pot ascunde cazuri de clientelism, precum intervenții în favoarea unor companii private locale sau a unor donatori locali ai partidelor. Pentru a stabili însă neechivoc motivația unor astfel de demersuri este nevoie de altfel de demersuri și resurse care țin mai degrabă de jurnalismul de investigație. Totuși, aplicația le oferă celor interesați de astfel de investigații o resursă importantă de care se poate pleca.
</p>

<p>
Implicarea în activități de reprezentare locală este unul din criteriile pe baza căruia poate fi judecată activitatea unui parlamentar. Cetățenii sau politicienii însăși pot considera mult mai importantă specializarea deputatului într-un domeniu de politici publice care să permită participarea la crearea unui cadrul legislativ adecvat sau controlul acțiunilor guvernului în acel domeniu. OpenParlament oferă acum posibilitatea de a monitoriza activitatea deputaților și de a o evalua pe ambele dimensiuni.
</p>

<h3>Referințe</h3>
<ul>
  <li>Chiru, M. 2014. 'Improving MPs’ Responsiveness through Institutional Engineering? Constituency Questions Under Two Electoral Systems', manuscris nepublicat.</li>
  <li>Martin, S. 2011. ‘Using Parliamentary Questions to Measure Constituency Focus: An Application to the Irish Case’, Political Studies, 59: 472–488</li>
  <li>Russo, F. 2011. ‘The Constituency as a Focus of Representation: Studying the Italian Case through the Analysis of Parliamentary Questions’, The Journal of Legislative Studies 17(3): 290-301.</li>
</ul>
"""


TEXT_MIGRATIONS = """\
<p>Te interesează să înțelegi de ce migrează parlamentarii și cum se leagă asta de restul problemelor partidelor și politicii românești? Citește analizele OpenPolitics despre <a href="http://www.openpolitics.ro/noutati/homepage/parlamentarii-migreaza-cauze-consecinte-si-explicatii-comparative.html">cauzele</a> și consecințele migrației parlamentare și despre <a href="http://www.openpolitics.ro/noutati/homepage/migratie-pana-la-capatul-golirii-de-sens-partidelor-politice.html">rolul partidelor</a> în acest fenomen.</p>

<iframe class="youtube" width="745" height="465" src="//www.youtube.com/embed/9mYRAv28F7c" frameborder="0" allowfullscreen></iframe>
"""


TEXT_POLICY = """\
<p>OpenParlament pune la dispoziția organizațiilor non-guvernamentale și cetățenilor interesați, într-un mod ușor de înțeles și utilizat, informații ce permit urmărirea și monitorizarea procesului legislativ pe 15 domenii de politici publice:</p>
"""


TEXT_POLICY_MORE = """\
<p>Toate inițiativele legislative și întrebările parlamentare din aceste domenii sunt incluse în categoria corespunzătoare utilizând două tipuri de informații. Pentru inițiativele legislative domeniul este stabilit prin analizarea comisiei parlamentare permanente la care Biroul permanent a trimis propunerea de lege pentru examinare. Conform Regulamentului Camerei Deputaților, Biroul permanent sesizează comisia permanentă "în competenţa căreia intră materia reglementată prin proiectul sau propunerea respectivă" (Art. 62, p. 23).</p>

<p>Pentru întrebarile și interpelările parlamentare domeniul de politici publice este stabilit prin analizarea ministerului căreia îi sunt adresate acestea. Compatibilitatea celor două tipuri de indicatori este asigurată de paralelismul dintre jurisdicția comisiilor parlamentare permanente și cea a ministerelor în sistemul parlamentar românesc.</p>
"""


TEXT_PROPOSAL_CONTROVERSY = """\
<p>Secțiunea <strong>legi controversate</strong> permite monitorizarea procesului legislativ al unor propuneri și proiecte de lege, inițiate în această legislatură, care au fost considerate problematice de către media, organizații non-guvernamentale sau experții Median Research Centre. Fiecare propunere legislativă din această secțiune este însoțită de detalii asupra controversei stârnite și de link-uri către articolele din media sau luările de poziție ale organizațiilor non-guvernamentale referitoare la aceasta.</p>

<p>Lista legilor controversate va fi actualizată periodic, dă-ne un semn dacă știi o propunere de lege care ar merita inclusă în această categorie.</p>
"""


TEXT_SOCIAL = """\
<h3>Comunicăm și pe</h3>
<div class="icons">
    <a href="http://www.facebook.com/OpenPolitics.ro">
        <img src="/static/img/icons/facebook.jpg" />
    </a>

    <a href="https://plus.google.com/104858678072022158034/">
        <img src="/static/img/icons/google-plus.jpg" />
    </a>
    <a href="http://www.youtube.com/user/OpenPoliticsRO?feature=watch">
        <img src="/static/img/icons/youtube.jpg" />
    </a>
</div>
"""


TEXT_VOTING_CONTROVERSY = """\
<h2>Voturi controversate</h2>

<p>Secțiunea <strong>voturi controversate</strong> prezintă și explică votul fiecărui deputat asupra unor proiecte de lege și propuneri legislative inițiate în această legislatură sau în precedentele, care au fost considerate problematice de către media, organizații non-guvernamentale sau experții Median Research Centre.</p>
"""


TEXT_VOTING_CONTROVERSY_MORE = """\
<p>Aceste voturi acoperă o gamă largă de subiecte: de la probleme de mediu și patrimoniu cultural (ex.: Roșia Montană) la probleme de etică aplicată (ex.: obligativitatea consilierii psihologice înainte de avort), de la aspecte ce țin de libertatea presei și libertatea de expresie (ex.: reincriminarea insultei și a calomniei) până la reglementări legate de funcționarea justiției (ex. scoaterea parlamentarilor și altor demnitari aleși de sub incidența conflictului de interese).</p>

<p>Desigur, disciplina la vot a parlamentarilor este necesară pentru implementarea politicilor publice asumate de guvern sau pentru menținerea profilului ideologic în cazul partidelor de opoziție. De aceea, parlamentarii votează de multe ori urmând doar decizia indicată de expertul partidului în acel domeniu, respectiv de liderii grupului parlament.</p>

<p>Totuși, dincolo de aceste circumstanțe, poziția parlamentarului asupra unor subiecte foarte delicate sau intens mediatizate rămâne un criteriu valid pentru decizia de vot de la alegerile următoare. Compararea propriei poziții asupra subiectelor respective cu cea a deputatului reprezintă un prim pas spre stabilirea gradului de compatibilitate sau incompatibilitate ideologică, un criteriu extrem de important pentru modul de funcționare al democrației reprezentative dar și pentru misiunea OpenParlament.</p>

<p>Caută <a href="/persoane/">aici</a> deputatul care te reprezintă sau de care ești interesat pentru a vedea cum a votat în cazul acestor propuneri. Lista voturilor controversate va fi actualizată periodic, folosind, sperăm, și contribuția dumneavoastră, a utilizatorilor.</p>
"""
