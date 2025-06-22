Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

#Install dependencies
pip install -r requirements.txt


#create a .env file like:
SECRET_KEY=your-django-secret
DEBUG=True
DB_NAME=ITS_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

#Run migrations
python manage.py makemigrations
python manage.py migrate

#Start the development server
python manage.py runserver







































You can get your **Google Maps API key** by creating a project in the Google Cloud Console and enabling the appropriate APIs. Here's how you can do it step by step:

---

### 🔐 How to Get a Google Maps API Key

1. **Go to Google Cloud Console**  
   → [https://console.cloud.google.com](https://console.cloud.google.com)

2. **Create or Select a Project**
   - If you don’t have a project yet, click “New Project”
   - Give it a name (e.g. `ITS_Backend_Geolocation`) and create it

3. **Enable Billing**
   - Go to “Billing” and link a billing account (Google offers a free monthly quota)

4. **Enable the Required API**
   - In the search bar, look for **“Geocoding API”**
   - Click “Enable”  
   - You may also want to enable **“Maps JavaScript API”** if you’ll use maps in the frontend

5. **Generate an API Key**
   - In the sidebar, go to **“APIs & Services” > “Credentials”**
   - Click **“Create Credentials” > “API key”**
   - Copy the generated key and paste it into your `.env` file:
     ```
     GOOGLE_MAPS_API_KEY=your_key_here
     ```

6. **Secure the Key**
   - Under “API restrictions,” restrict the key to only the services you need (like Geocoding)
   - Under “Application restrictions,” you can limit usage to your backend IP or frontend domains

---
