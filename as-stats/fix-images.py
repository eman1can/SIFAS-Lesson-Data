from os import listdir

for file in listdir():
    if not file.endswith('html'):
        continue
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        content = content.replace('https://as.lovelive.eu.org/images_b95/', 'file:///E:/CodeProjects/SIFAS/lessons/as-stats/')
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)