隊伍名稱：手護你的音
作品名稱：手語翻譯系統
主題領域：運動健康、教育科技、資料收集應用
使用者角色：聾人、聽障者
核心 FHIR Resources：Observation
Demo 入口：
操作步驟:
1.下載環境(所需環境位於下方)
2.啟動 FHIRapp.py
3.啟動後終端會給三個網址長這樣:
    Running on all addresses (0.0.0.0)    (伺服器監聽)
    Running on http://127.0.0.1:5000      (本地測試)
    Running on http://172.20.10.4:5000    (手機連線)
    第二個網址是給本機測試的，但電腦沒有陀螺儀感測器等，所以請使用第三個網址，又因為蘋果手機在內網調取感測器權限時，會無法調取，所以需要將網站至於外網上，所以下方我會提供一個第三方軟件，可以在不用租借網域的情況下快速的將內網網站放置於外網上。
4.下載 ngrok
    網址 https://ngrok.com/download
5.註冊並設定 Token
    註冊 ngrok 帳號
    登入後取得 Authtoken
    在終端機輸入：ngrok config add-authtoken 你的Token
    確認 FHIRapp.py 已啟動
    確認出現 Running on http://127.0.0.1:5000
6.啟動 ngrok 的終端   
    輸入 ngrok http 5000
7.取得公開網址
    執行後會出現 Forwarding  https://xxxx.ngrok-free.app -> http://localhost:5000
8.將 https://xxxx.ngrok-free.app 分享給使用者便可即刻使用此網站

所需環境:
1.flask==3.0.0
2.flask-cors==4.0.0
3.numpy==1.26.4
4.joblib==1.3.2


