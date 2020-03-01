#!/usr/bin/env python3
"""
vkdocs.py - скрипт для поиска публичных документов
пользователя в VK.
* id - id пользователя: '123' или 'id123' или 'anon_228'
* from document - id документа, с которого начнется поиск.
  По умолчанию приблизительно возможный id последнего документа в VK.
* access_token - токен, полученный в ходе авторизации.
  При первом вводе сохраняется в файле token.txt
Ссылки на найденные документы сохраняются в папке /out

В версии 1.4.2:
    - добавлен параметр версии для запросов к ВК
    - созраненный access token теперь не показывается полностью

В версии 1.4.1:
    - добавлен вывод невалидных ответов ВК чтобы разобраться в чем дело 

В версии 1.4:
    - немного увеличена скорость работы

В версии 1.3:
    - добавлены костыли
    - стало ясно, что "BadStatusLine" не исправлено

В версии 1.2:
    - исправлены "ConnectionReset" и "BadStatusLine"

В версии 1.1:
    - исправления некоторых ошибок
    - добавлен параметр from document

Radiokot | radiokot.com.ua
С любовью для /r
"""

import http.client, sys, time, json, time, os

# Открытие соединения с VK.
def getApiConnection():
    return(http.client.HTTPSConnection("api.vk.com"))

# Запрос к API VK.
def vkRequest(apiConnection, url, body = ""):
    url = url + "&v=5.71"
    apiConnection.request("POST", url, body)
    vkResponse = apiConnection.getresponse().read()
    jsonString = vkResponse.decode("utf-8")
    vkJson = json.loads(jsonString)

    # Обработка Too many requests per second.
    if vkJson.get("response", 0) == 0:
        error = vkJson.get("error", 0)
        if error != 0 and error.get("error_code", 0) == 6:
            time.sleep(0.35)
            return(vkRequest(apiConnection, url, body))
        elif error == 0:
            print("Unexpected error:", jsonString[:200])
            time.sleep(2)
            return(vkRequest(apiConnection, url, body))
        
    return(vkJson)

# Вывод прогресса поиска.
def showProgress(fromId, toId, foundCount):
    print("Total found: " + str(foundCount) + ", current range: " +
          str(fromId) + " - " + str(toId))

    
# Читаем id.
id = input("Enter user ID: ").replace(" ", "")

# Получаем верхнюю границу поиска по самому тупому предположению.
fromDoc = round(53376090 + (int(time.time()) - 1329165420 ) * 2.2185)
# Предлагаем ее изменить.
print("Enter start document (" + str(fromDoc) + " if empty): ", end="")
fromDocInput = input().replace(" ", "")
if fromDocInput != "":
    try:
        fromDocInputInt = int(fromDocInput)
        if fromDocInputInt > 0:
            fromDoc = fromDocInputInt
        else:
            raise ValueError()
    except ValueError:
        print("Invalid start document. Using " + str(fromDoc) + " unstead")

# Читаем токен из файла или ввода.
try:
    with open("token.txt", "r") as tokenFile:
        token = tokenFile.readline()
    if len(token) == 0:
        raise Exception
    print("access_token (saved): " + token[:10] + "...")
except:
    token = input("access_token: ").replace(" ", "")

# Инициализируем соединение с API.
print("\nInit connection...\n")
apiConnection = getApiConnection()

# Пробуем зарезолвить id, попутно проверяя токен.
while True:
    try:
        vkResponse = vkRequest(apiConnection, "/method/execute.getProfile?id=" + id + "&access_token=" + token)
    except:
            apiConnection.close()
            time.sleep(2)
            apiConnection = getApiConnection()
            continue
        
    if vkResponse.get("response", 0) in (0, None):
        # Если ошибка в execute, то, скорее всего, неправильный id.
        if vkResponse.get("execute_errors", 0) != 0:
            print(vkResponse.get("execute_errors")[0].get("error_msg"))
        # Иначе что-то с токеном.
        else:    
            errorCode = vkResponse.get("error", 0).get("error_code", 0)
            # Токен не подходит если есть ошибка 5 (запретили доступ) или 10 (он просто не тот).
            if errorCode in (5, 10):
                print("Invalid access_token")
            # Хз что тут может быть, скриньте в тред если что.    
            else:
                print("Something wrong: " + str(vkResponse))
        # В любом случае это плохо и дальше работать не стоит.        
        sys.exit()
    break

id = str(vkResponse.get("response"))

# Нормально все, да? Значит можно работать.

# Сохраним токен в файл, раз он нормальный.
with open("token.txt", "w") as tokenFile:
    tokenFile.write(token)

# Идем от новых к старым.
# В чем суть: локально генерируем некоторое количество доков,
# потом к ним на сервере ВК добавляется еще 400.
currentDoc = fromDoc
totalFound = 0
uid = id + "_"

if not os.path.exists("out"):
    os.makedirs("out")
outFileName = "out/docs" + id + ".txt"

print("User ID: " + id + ", output file: " + outFileName)

with open(outFileName, "w") as outFile:
    while currentDoc > 0:
        preDocs = "preDocs="
        startDoc = currentDoc

        # С этим параметром можно играться,
        # но чем больше засовывать документов в запрос тем дольше он будет выполняться.
        # Max - 8970.
        while (len(preDocs) < 4000):
            preDocs += uid + str(startDoc) + ","
            startDoc -= 1
        preDocs = preDocs[:-1]

        url = "/method/execute.findDocs?uid=" + id + "&from=" + str(startDoc) + "&access_token=" + token

        try:
            vkResponse = vkRequest(apiConnection, url, preDocs).get("response", 0)
        except (KeyboardInterrupt, SystemExit):
            print("Bye!")
            exit()
        except:
            apiConnection.close()
            time.sleep(2)
            apiConnection = getApiConnection()
            continue
                
        if vkResponse == None:
            continue

        try:
            lastDoc = vkResponse.get("to")
            found = vkResponse.get("found")
            currentFoundCount = len(found)
            totalFound += currentFoundCount
        except:
            print("\n" + str(url))
            print("\n" + str(vkResponse))
            time.sleep(5)
            continue
        
        if currentFoundCount > 0:
            for item in found:
                outFile.write(item.get("url", 0) + "\n")
                outFile.flush()
  
        showProgress(currentDoc, lastDoc, totalFound)
        currentDoc = lastDoc

print("\nDone! Found: " + str(totalFound))
apiConnection.close()        
