"""Retire installation/removal offers without rewriting technical or customer history."""
from __future__ import annotations
import html
import json
import re

EXACT = {
 'Klima Bakımı, Tamiri, Montaj ve Gaz Dolumu':'Klima Bakımı, Tamiri ve Gaz Kontrolü',
 'periyodik klima bakımı, söküm-montaj ve arıza onarımı':'periyodik klima bakımı ve arıza onarımı',
 ', vakumlu montaj, söküm-yer değişimi, su akıtma':', su akıtma',
 ', vakumlu montaj, su akıtma':', su akıtma',
 'Soğutma, ısıtma, bakım ve montaj ihtiyaçları. İç ve dış ünite belirtilerinden doğru yerden başlayın.':'Soğutma, ısıtma, bakım ve onarım ihtiyaçları. İç ve dış ünite belirtilerinden doğru yerden başlayın.',
 'Kombi tamiri veya bakımı; klima bakım, onarım, montaj ve yer değişimi için bulunduğunuz bölgeyi ve cihazınızın markasını birlikte belirtin.':'Kombi tamiri veya bakımı; klima bakım ve onarımı için bulunduğunuz bölgeyi ve cihazınızın markasını birlikte belirtin.',
 'Kombi, klima ve ısıtma tesisatı için bakım, tamir, montaj ve kontrol kapsamlarını inceleyin.':'Kombi, klima ve ısıtma tesisatı için bakım, tamir ve kontrol kapsamlarını inceleyin.',
 'İç ve dış ünitenin konumu, boru güzergâhı, drenaj ve elektrik bağlantısı şartları montajdan önce değerlendirilir. Dış üniteye erişim, kat ve mevcut montaj bilgilerini randevuda belirtin.':'Mevcut iç ve dış ünitenin modeli, gözlenen belirti ve güvenli erişim koşulları kontrol öncesinde değerlendirilir. Filtre bakım geçmişini ve etkilenen odayı randevu görüşmesinde belirtin.',
 'Taşınma veya yer değişimi için mevcut ve yeni konumu, cihazın modelini ve dış üniteye erişim koşullarını paylaşın. Söküm ve yeniden montajın kapsamı birbirinden ayrı açıklanır.':'Mevcut cihazın soğutmama, ısıtmama veya su damlatma belirtisini seçin. Cihaz modeli ve güvenli erişim bilgisiyle uygun bakım veya onarım kapsamı görüşülür.',
 'Klima için bakım, onarım ve montaj talebini birlikte yazabilir miyim?':'Klima için bakım ve onarım ihtiyacını birlikte yazabilir miyim?',
 'İhtiyaçları aynı talepte belirtebilirsiniz; her işlemin kapsamı ayrı değerlendirilir. Mevcut arıza için belirti ve model, montaj için ünite konumu ve erişim bilgisi gerekir. Sadece marka adı bütün işlemlerin uygunluğunu belirlemez.':'Bakım ve onarım ihtiyacını aynı talepte belirtebilirsiniz; her işlemin kapsamı ayrı değerlendirilir. Mevcut arızayı, cihaz modelini ve ünitelere güvenli erişim bilgisini paylaşın. Sadece marka adı yapılacak işlemi belirlemez.',
 'Klima için servis ararken önce mevcut cihazda bir sorun mu yaşadığınızı, bakım mı istediğinizi yoksa montaj veya taşınma mı planladığınızı belirtin. Bu ihtiyaçlar aynı randevuda görüşülebilir; ancak hazırlanacak ekipman, erişim bilgisi ve yapılacak kontrol birbirinden farklıdır. Yalnızca marka adını söylemek işlem kapsamını belirlemeye yetmez.':'Klima için servis ararken mevcut cihazda bir sorun mu yaşadığınızı, yoksa periyodik bakım mı istediğinizi belirtin. Bakım ve onarım ihtiyacı aynı görüşmede değerlendirilebilir; cihazın modeli, gözlenen belirti ve ünitelere erişim bilgisi gereken kontrolün planlanmasına yardımcı olur.',
 'Onarım, bakım ve yeni montaj ayrı kapsamlarla görüşülür.':'Onarım ve bakım ayrı kapsamlarla görüşülür.',
 'Tahtakale veya Yeşilkent için kayıt açarken taşınma nedeniyle söküm mü, mevcut cihazda arıza mı istediğinizi seçin. Yer değiştirmede eski ve yeni konum ayrı değerlendirilir.':'Tahtakale veya Yeşilkent için kayıt açarken mevcut cihazda bakım mı, arıza kontrolü mü istediğinizi belirtin.',
 'Yeni montaj veya yer değişimi düşünülüyorsa mevcut bağlantılar ve yeni yerin uygunluğu ayrıca incelenir.':'Mevcut bağlantıların görünür durumunu yalnız güvenli bir noktadan tarif edin.',
 'İşlem ve ücret kontrol sonrası görüşülür; formdaki ilk talep görülmeyen bütün montaj ayrıntılarına onay sayılmaz.':'Bakım veya onarım kapsamı ve ücret kontrol sonrasında görüşülür; ilk talep ek işlemler için onay sayılmaz.',
 'Montaj veya yer değiştirme talebinizde yeni konumun fotoğrafı, boru hattının görünen yönü ve dış ünitenin erişim durumu ayrıca değerlendirilir. Temizlik, drenaj kontrolü ve montaj aynı işlem değildir; uygulanacak kapsam kontrol sonrasında açıklanmalıdır.':'Mevcut ünitenin konumunu ve güvenli erişim durumunu belirtin. Temizlik ile drenaj onarımı aynı işlem değildir; uygulanacak kapsam kontrol sonrasında açıklanır.',
 'Yeni montaj veya yer değişimi düşünülüyorsa gerekli izin ve erişimin kimle görüşüleceğini açıklayın; bu sayfa herhangi bir bina için uygulama onayı vermez.':'Ortak alana erişim gerekiyorsa bu alanı açabilecek kişinin kim olduğunu görüşmede belirtin.',
 'Yer değiştirme düşünülüyorsa eski ve yeni konum birbirinden ayrı tarif edilmelidir.':'Cihaz daha önce taşındıysa önceki kullanım yeri ile bugünkü arızayı ayrı tarif edin.',
 'Her bölümün talebi bakım mı, çalışmama mı, yeni montaj mı diye ayrıca belirtilmelidir.':'Her bölümün talebi bakım mı, çalışmama veya başka bir arıza mı diye ayrıca belirtilmelidir.',
 'Klima bakımında mevcut cihazın temizliği, onarımda çalışma belirtisi, yer değişiminde ise eski ve yeni konum birlikte konuşulur.':'Klima bakımında mevcut cihazın temizlik ihtiyacı, onarımda ise gözlenen çalışma belirtisi konuşulur.',
 '500 Evler klima görüşmesinde bakım, arıza veya söküm talebinizi seçin.':'500 Evler klima görüşmesinde bakım veya arıza talebinizi seçin.',
 'Bakım, montaj, söküm veya gaz/kaçak kontrolü isteğinizi ayrı yazın. Montajda konum ve erişim koşulları, gaz işleminde cihaz etiketi ve teknik kontrol önemlidir.':'Bakım, onarım veya gaz/kaçak kontrolü isteğinizi ayrı yazın. Cihaz etiketi, görülen belirti ve güvenli erişim bilgisi teknik kontrolün planlanmasına yardımcı olur.',
 'Suyun görüldüğü yer ile bakım veya montaj talebini ayrı anlatmaya yardımcı rehberler.':'Suyun görüldüğü yer ile bakım veya onarım ihtiyacını ayrı anlatmaya yardımcı rehberler.',
 'Temizlik, montaj düzenlemesi ve teknik arıza kontrolünün hangisinin istendiği net olmalı;':'Temizlik veya teknik arıza kontrolünün hangisinin istendiği net olmalı;',
 'Montaj ve taşıma için mevcut yer ile düşünülen yeni konumu ayrı tarif etmeniz değerlendirmeyi kolaylaştırır.':'Mevcut iç ve dış ünitenin konumunu ve gördüğünüz belirtiyi ayrı tarif etmeniz değerlendirmeyi kolaylaştırır.',
 'Yeni kurulum veya yer değişimi planlıyorsanız site koşullarıyla erişim gereksinimini randevudan önce konuşabiliriz.':'Bakım veya arıza kontrolü için ünitelere erişim gereksinimini randevu görüşmesinde belirtebilirsiniz.',
 'Ünite yeri ve montaj beklentisi':'Mevcut üniteye güvenli erişim',
 'Montaj ve yer değişimi öncesinde alanı konuşun':'Mevcut dış ünitenin erişimini konuşun',
 'Kontrol, bakım ve yeniden montaj seçenekleri':'Arıza kontrolü ve bakım kapsamları',
 'Montaj kararı için yer bilgisini ön görüşmeye hazırlayın':'Mevcut cihazın yer bilgisini ön görüşmeye hazırlayın',
 'Yer değiştirme işleminde iki konumu birlikte görüşün':'Önceki kullanım yeri ile bugünkü belirtiyi ayırın',
 'Söküm veya yeni montajı önceden belirtin':'Bakım veya onarım ihtiyacını önceden belirtin',
 'Yeşilköy ve Şenlikköy taleplerinde söküm sonrası hedefi yazın':'Yeşilköy ve Şenlikköy taleplerinde güncel adresi yazın',
 'Klima montajı ve mevcut sistemin eşleşmesi':'Mevcut sistemde iç ve dış ünite eşleşmesi',
 'Bebek veya Etiler’de yeni montaj beklentisini ayırın':'Bebek veya Etiler’de mevcut cihazın ihtiyacını ayırın',
 'Söküm ve yer değiştirme arızadan farklıdır':'Bakım ile arıza kontrolü farklı kapsamlardır',
 'Bakım, söküm ve soğutmama işlerini aynılaştırmayın':'Bakım ile soğutmama belirtisini ayrı anlatın',
}
# Full-paragraph offers replaced with relevant existing-equipment information.
PARAGRAPHS = {
 'Dış ünitenin yerini değiştirmek istiyorsanız':'Dış ünitenin mevcut yerini ve güvenli erişimin nasıl sağlandığını belirtin. Ortak alan, çatı veya cepheye kendiniz çıkmayın. Bakım ve arıza kontrolü için gerekli erişim yöntemi görüşmede netleştirilir.',
 'Arıza kontrolünde mevcut çalışmanın neden aksadığı araştırılır; bakımda':'Arıza kontrolünde mevcut çalışmanın neden aksadığı araştırılır; bakımda ise cihazın koşullarına uygun temizlik ve kontroller değerlendirilir. Esenler’deki mahalle seçimi, bu iki ihtiyacı aynı işleme dönüştürmez. Belirlenen kapsam ve ücret açıklanarak onayınız alınır.',
 'Avcılar listesinde Tahtakale ve Merkez ayrı mahalle seçenekleridir. Klimanın':'Avcılar listesinde Tahtakale ve Merkez ayrı mahalle seçenekleridir. Mevcut cihazın bulunduğu güncel adresi ve etkilenen üniteyi kaydedin. Cihaz daha önce taşındıysa bunu geçmiş bilgi olarak belirtin; önceki işlem yeni arızanın kesin nedeni sayılmaz.',
 'Bahçeşehir 1. Kısım veya Şamlar adresindeki yeni kurulumda':'Bahçeşehir 1. Kısım veya Şamlar adresindeki mevcut cihazın iç ve dış ünite modellerini birlikte kaydedin. Soğutmama belirtisinde seçili mod ve etkilenen odayı açıklayın; ölçüm yapılmadan gaz ekleme veya parça gereksinimi kesinleştirilmez.',
 'Mimaroba’daki bir cihaz başka bir mahalleye taşınacaksa':'Mimaroba’daki mevcut cihaz başka bir adresten gelmişse önceki çalışma durumunu bildiğiniz kadarıyla aktarın. Bugün görülen belirtiyi ve mevcut adresi ayrı kaydedin; geçmişte çalışmış olması şu anki teknik durumunu kanıtlamaz.',
 'Mevcut klimayı başka yere götürmek ya da yeni bir konuma kurmak istiyorsanız':'Mevcut klimanın bakım ihtiyacını ve varsa çalışma sorununu ayrı belirtin. Dış ünitenin erişimi ortak alan üzerinden sağlanıyorsa bunu görüşmede açıklayın. Önerilen kontrol, işlem ve ücret onayınıza sunulur.',
 'Yakuplu veya Adnan Kahveci adresinde bir klimayı taşıtacaksanız':'Yakuplu veya Adnan Kahveci adresindeki klimanız için bakım ve arıza gözlemlerini ayrı paylaşın. Daha önceki kullanım yeri veya işlem tarihini biliyorsanız not edin. Boru hattına ya da dış üniteye müdahale etmeden güvenli teknik kontrol planlayalım.',
 'Cihazı yalnız depolamak için söktürmekle başka adreste yeniden kurdurmak':'Mevcut cihazın güncel çalışma durumunu ve ekrandaki uyarıyı bildiğiniz kadarıyla anlatın. Eski servis kaydı başka adrese aitse bugünkü adresi ayrıca seçin. Önceki bakım veya kullanım bilgisi, yeni belirti için tek başına teşhis sayılmaz.',
 'Talebiniz bakım, onarım veya yeni montaj olabilir.':'Talebiniz bakım veya onarım için olabilir. Mevcut cihazın belirtisi, modeli ve ünitelere güvenli erişim durumu birlikte değerlendirilir. Kilyos adresinizi belirtmek randevu yerini tanımlar; uygunluk ve işlem ücreti görüşmede netleşir.',
 'Dış ünite balkon, çatı, bahçe veya dış cephede olabilir;':'Dış ünite balkon, çatı, bahçe veya dış cephede olabilir; bulunduğu yeri yalnız güvenli konumunuzdan tarif edin. Ortak alanın açılması gerekiyorsa ilgili kişiyi görüşmede belirtin. Bakım ve arıza kontrolü için güvenli erişim yöntemi ayrıca değerlendirilir.',
 'Klimanın oda içindeki konumu ve dış ünitenin güvenli bir noktadan':'Klimanın oda içindeki konumunu ve dış ünitenin güvenli bir noktadan görülebilen yerini açıklayın. Bakım veya arıza kontrolü için kilitli ortak alanın açılması gerekiyorsa bunu önceden belirtin. Fotoğraf almak için riskli bir alana çıkmayın.',
 'Taşınan klimanın yeniden kurulması, çalışan cihazın bakımı':'Çalışan cihazın bakımı ile arızalı cihazın kontrolü farklı hazırlıklar gerektirebilir. Daha önce taşınmış bir cihaz varsa model ve önceki çalışma bilgisini kayda ekleyin. Mevcut belirti ve güvenli erişim koşulları üzerinden kontrol kapsamı belirlenir.',
 'Yeni klima yerleşiminde dış ünite için düşünülen bölüm':'Mevcut bir dış üniteye birden fazla iç ünite bağlıysa hangi odanın etkilendiğini söyleyin. İç ve dış ünite model bilgileri birlikte gerekebilir. Başka bir dairedeki cihazın davranışı, kendi sisteminiz için kesin arıza sonucu vermez.',
 'Yeni montajda önerdiğiniz dış ünite konumunu':'Dış ünitenin mevcut konumunu ve güvenli erişimin nasıl sağlanabileceğini belirtin. Klima kapağını sökmek, çatıya çıkmak veya pencere dışına uzanmak hazırlık işi değildir. Kontrol için gereken erişim görüşmede değerlendirilir.',
 'Yeni cihaz için yer danışmak, mevcut klimayı onartmak':'Mevcut klimayı onartmak veya periyodik bakım istemek farklı ihtiyaçlardır. Etiketteki model bilgisini ve gözlenen belirtiyi paylaşın. Ortak alan erişimi gerekiyorsa bunu ilgili kişilerle görüşün; bu sayfa cephe müdahalesine izin vermez.',
 'Klimayı başka odaya veya başka adrese taşıtmak istiyorsanız':'Mevcut klimanın modelini, gözlenen belirtiyi ve son normal çalışma zamanını paylaşın. Bakım istemek, ayrıca fark edilen arızanın onarıldığı anlamına gelmez. Kontrol sonucunda önerilen kapsam ve ücret ayrı açıklanır.',
 'Mekân taşındıysa söküm ve yeni yere montajı;':'Mekân daha önce taşındıysa cihazın geçmiş kullanımını ve bugünkü soğutma sorununu ayrı tarif edin. Yakın zamanda temizlik yapılması bütün arızaların kontrol edildiği anlamına gelmez. Dış üniteye yaklaşmak için çatıya veya raf üzerine çıkmayın; güvenli erişim yöntemini görüşmede belirtin.',
}


def correct_retired_copy(files: dict[str, bytes]) -> dict:
    changed=[];counts={'literal_replacements':0,'offer_paragraphs':0,'visible_review_option_labels':0}
    def literals(text):
        for old,new in EXACT.items():
            n=text.count(old)
            if n:text=text.replace(old,new);counts['literal_replacements']+=n
        return text
    for name in list(files):
        if not name.endswith('.html') or name in {'klima-montaji.html','klima-sokumu.html'}:continue
        raw=files[name].decode();text=raw
        # Installation titles and code facts in technical tables are immutable.
        chunks=re.split(r'(<table\b[^>]*>[\s\S]*?</table>)',text,flags=re.I)
        for i in range(0,len(chunks),2):
            value=chunks[i]
            if name=='index.html':
                # Preserve all historical customer review bodies and old backend enum values.
                old='Soğutma, ısıtma, bakım ve montaj ihtiyaçları. İç ve dış ünite belirtilerinden doğru yerden başlayın.'
                value=value.replace(old,EXACT[old]);counts['literal_replacements']+=int(old in chunks[i])
                value,n=re.subn(r'(<option\b[^>]*value="Klima Bakımı / Montajı"[^>]*>)Klima bakımı / montajı(</option>)',r'\1Klima bakımı / onarımı\2',value)
                counts['visible_review_option_labels']+=n
            else:
                value=literals(value)
                def para(m):
                    plain=html.unescape(re.sub(r'<[^>]+>','',m['body']))
                    for start,replacement in PARAGRAPHS.items():
                        if plain.startswith(start):
                            counts['offer_paragraphs']+=1
                            return m['open']+html.escape(replacement)+m['close']
                    return m[0]
                value=re.sub(r'(?P<open><p\b[^>]*>)(?P<body>.*?)(?P<close></p>)',para,value,flags=re.S)
            chunks[i]=value
        text=''.join(chunks)
        if name=='hizmetler.html':
            text=text.replace('>Klima montajı</h3>','>Klima filtre kontrolü</h3>')
            text=text.replace('>Klima sökümü ve yer değişimi</h3>','>Klima arıza kontrolü</h3>')
        if text!=raw:files[name]=text.encode();changed.append(name)
    return {'files_changed':changed,'counts':counts,'scope':'Service offers only; model tables, manual titles and historical customer reviews are preserved.'}
