import os
import pathlib
import requests
from flask import url_for
from flask import Flask, render_template, request, jsonify, abort, redirect, session, flash
import mysql.connector
from datetime import datetime
from mysql.connector import Error
from fetch import get_cloud_data  # Adjusted function to fetch and store cloud data
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests

app = Flask(__name__)
app.secret_key = "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"  # Change this to a secure random string

# Google OAuth2 Configuration
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Allow HTTP traffic for local development
GOOGLE_CLIENT_ID = "973444997965-8qvk6df1psjqm0p3c4dq127u16g5t3nc.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "clientSecret.json")

flow = Flow.from_client_secrets_file(
    'clientSecret.json',  # Path to your downloaded client secret JSON file
    scopes=[
        'https://www.googleapis.com/auth/userinfo.profile', 
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'
    ],
    redirect_uri='http://127.0.0.1:5000/index'  # Your redirect URI
)

# Google login required decorator
def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper

# Google Login Route
@app.route("/google-login")
def google_login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

# Google OAuth callback route
@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    token_request = google.auth.transport.requests.Request(session=request_session)
    
    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    google_id = id_info.get("sub")
    name = id_info.get("username")
    email = id_info.get("email")

    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Check if user exists in the database
        cursor.execute("SELECT * FROM users WHERE google_id = %s", (google_id,))
        user = cursor.fetchone()

        if user:
            # Update last login time
            cursor.execute("UPDATE users SET last_login = %s WHERE user_id = %s", (datetime.now(), user['user_id']))
            connection.commit()
        else:
            # Insert new user
            cursor.execute(
                "INSERT INTO users (google_id, username, email, last_login) VALUES (%s, %s, %s, %s)",
                (google_id, name, email, datetime.now())
            )
            connection.commit()
            user = {
                'user_id': cursor.lastrowid,
                'username': name,
                'email': email
            }

        # Set session
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['email'] = user['email']

        return redirect(url_for('profile'))

    except Error as e:
        return f"Database error: {str(e)}", 500
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


# Profile Page
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('google_login'))

    return render_template('profile.html', username=session['username'], email=session['email'])


###########################
### DATABASE CONNECTION ###
###########################
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'nacua',
    'database': 'cloud_data'
}

def create_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"[ERROR] Database connection failed: {e}")
        return None
    

@app.route('/')
def login():
    return render_template('login.html')


@app.route('/live-map')
def live_map():
    return render_template('windymap.html')

#################################
# Route for the main index page #
#################################
@app.route('/index')
def index():
    username = session.get('username','Guest')
    return render_template('index.html', username=username)  # Ensure you have an 'index.html' file in the templates folder

############################
# Handles the login process #
############################
@app.route('/login', methods=['POST'])
def handle_login():
    username = request.json.get('username')
    password = request.json.get('password')

    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch user data
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['user_id']  # Store the user ID in the session
            session['f_name'] = user['f_name']  # Store the user's first name in the session
            session['email'] = user['email'] 

            print(f"User  ID stored in session: {session['user_id']}")
            
            # Check if the user has access to the "View User" button (Jea and password 777)

            session['is_admin'] = (username == "quin" and password == "999")
            # session['is_user'] = (username == )

            return jsonify({
                'success': True,
                'message': 'Login successful',
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

##########################
## GET USERS NAME ########
##########################
@app.route('/get-user-fname')
def get_user_fname():
    user_id = session.get('user_id')  # Ensure `user_id` is stored in the session during login
    print(f"Fetching user name for user_id: {user_id}")  # Debug statement
    if user_id:
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Query to fetch first name
            query = "SELECT f_name FROM users WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            
            if user:
                print(f"User  found: {user['f_name']}")  # Debug statement
                return jsonify({'success': True, 'f_name': user['f_name']})
            else:
                print("User  not found in database.")  # Debug statement
                return jsonify({'success': False, 'f_name': 'Guest'})
        except Exception as e:
            print(f"Error fetching user name: {str(e)}")  # Debug statement
            return jsonify({'success': False, 'message': str(e)})
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
    print("User  ID not found in session.")  # Debug statement
    return jsonify({'success': False, 'f_name': 'Guest'})

            
##############################
# Handles the signup process #
##############################
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    try:
        connection = create_connection()
        cursor = connection.cursor()

        # Insert the new user into the database
        cursor.execute("INSERT INTO users (email, username, password) VALUES (%s, %s, %s)", (email, username, password))
        connection.commit()

        # Return the email and username for pre-filling the login form
        return jsonify({
            'success': True,
            'message': 'Signup successful',
            'email': email,
            'username': username
        }) 

    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


#########################################
# Get API data and store it in Database #
#########################################

@app.route('/get-stored-data', methods=['POST'])
def get_stored_data():
    data = request.get_json()
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])

    print(f"[DEBUG] Received Latitude: {latitude}, Longitude: {longitude}")
    

    try:
        # Establish connection to the database
        connection = create_connection()
        if connection is None:
            return jsonify({'success': False, 'message': 'Database connection not available.'})

        cursor = connection.cursor(dictionary=True)

        # Fetch locations ID
        cursor.execute('''SELECT location_id FROM locations
                          WHERE latitude = CAST(%s AS DECIMAL(10, 7))
                          AND longitude = CAST(%s AS DECIMAL(10, 7))''',
                       (latitude, longitude))
        locations = cursor.fetchone()

        # If locations is not found, fetch cloud cover data from the API
        if not locations:
            print("[DEBUG] Locations not found. Fetching from API...")
            result = get_cloud_data(latitude, longitude)
            if not result:
                return jsonify({'success': False, 'message': 'Failed to fetch or store data from API.'})

            connection.commit()  # Save changes

            # Re-fetch the locations ID after inserting new data
            cursor.execute('''SELECT location_id FROM locations
                            WHERE latitude = CAST(%s AS DECIMAL(10, 7))
                            AND longitude = CAST(%s AS DECIMAL(10, 7))''',
                        (latitude, longitude))
            locations = cursor.fetchone()

        # Handle case where locations is not found
        if not locations:
            print("[ERROR] Locations insertion or retrieval failed.")
            return jsonify({'success': False, 'message': 'Locations insertion failed.'})

        location_id = locations['location_id']
        print(f"[DEBUG] Found Locations ID: {location_id}")

        # Fetch hourly cloud cover data
        cursor.execute('''SELECT time, cloud_cover_total
                          FROM hourly_cloud_cover
                          WHERE location_id = %s
                          ORDER BY time ASC''', (location_id,))
        hourly_data = cursor.fetchall()

        # Fetch current cloud cover data
        cursor.execute('''SELECT * FROM current_cloud_cover
                          WHERE location_id = %s
                          ORDER BY time DESC LIMIT 1''', (location_id,))
        current_data = cursor.fetchone()

        # Check if data exists
        if not hourly_data or not current_data:
            return jsonify({'success': False, 'message': 'No Cloud Cover data found for this locations.'})

        # Prepare response
        response = {
            'success': True,
            'hourly': {
                'time': [row['time'].strftime('%Y-%m-%d %H:%M') for row in hourly_data],
                'cloud_cover_total': [int(row['cloud_cover_total']) for row in hourly_data]
            },
            'current': {
                'time': current_data['time'].strftime('%Y-%m-%d %H:%M'),
                'cloud_cover_total': f"{int(current_data['cloud_cover_total'])} %",
                'cloud_cover_low': f"{int(current_data['cloud_cover_low'])} %",
                'cloud_cover_mid': f"{int(current_data['cloud_cover_mid'])} %",
                'cloud_cover_high': f"{int(current_data['cloud_cover_high'])} %",
                'visibility': f"{int(current_data['visibility'])} Meters"
            }
        }
        
    except Error as e:
        print(f"[ERROR] Database error: {e}")
        response = {'success': False, 'message': f'Database error: {str(e)}'}
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

    print(f"[DEBUG] Response: {response}")
    return jsonify(response)

############################################
##### EDIT PROFILE AT USER ACCOUNT #########
############################################
@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('User  not logged in.', 'error')  # Flash an error message
        return jsonify({'success': False, 'message': 'User  not logged in.'}), 401  # Return an error if not logged in
    
    if request.method == 'GET':
        user_id = session['user_id']
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)

            # Fetch the user's current profile information from the database
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()

            # Return the user data as JSON for the modal
            return jsonify({'success': True, 'user': user})

        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()

    elif request.method == 'POST':
        data = request.form  # Form data
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        first_name = data.get('first_name')  # New field for first name
        last_name = data.get('last_name')    # New field for last name

        user_id = session['user_id']

        # Prepare the update statement and parameters
        update_fields = []
        update_values = []

        if email:
            update_fields.append("email = %s")
            update_values.append(email)
        if username:
            update_fields.append("username = %s")  # Ensure this matches your database column
            update_values.append(username)
        if password:
            update_fields.append("password = %s")
            update_values.append(password)
        if first_name:
            update_fields.append("f_name = %s")  # Ensure this matches your database column
            update_values.append(first_name)
        if last_name:
            update_fields.append("l_name = %s")    # Ensure this matches your database column
            update_values.append(last_name)

        # If no fields are provided, return an error
        if not update_fields:
            return jsonify({'success': False, 'message': 'At least one field must be provided for update.'}), 400

        # Add user_id to the parameters
        update_values.append(user_id)

        try:
            connection = create_connection()
            cursor = connection.cursor()

            # Create the SQL update statement
            sql_update = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s"
            cursor.execute(sql_update, update_values)
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'No rows updated. User may not exist.'}), 404

            # Update session with new information if applicable
            if email:
                session['email'] = email
            if username:
                session['username'] = username
            if first_name:
                session['first_name'] = first_name
            if last_name:
                session['last_name'] = last_name

            return jsonify({'success': True, 'message': 'Profile updated successfully.'})

        except Exception as e:
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()



####################
# User Information #
####################
@app.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if request.method == 'GET':
        # Fetch user information for editing
        try:
            connection = create_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()

            if user:
                return render_template('edit_user.html', user=user), 200
            else:
                return jsonify({'success': False, 'message': 'User not found'}), 404

        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()

    elif request.method == 'POST':
        # Handle user account update
        data = request.json
        f_name = data.get('f_name')
        l_name = data.get('l_name')
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        # Validate inputs
        if not f_name or not l_name or not email or not username or not password:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400

        try:
            connection = create_connection()
            cursor = connection.cursor()

            # Update user information in the database
            cursor.execute(
                "UPDATE users SET f_name=%s, l_name=%s, email=%s, username=%s, password=%s WHERE user_id=%s",
                (f_name, l_name, email, username, password, user_id)
            )
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'No rows updated. User may not exist.'}), 404

            return jsonify({'success': True, 'message': 'Account updated successfully.'})

        except Error as e:
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
#################
## DELETE USER ##
#################
@app.route('/delete-user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    logged_in_user_id = session.get('user_id')  # Retrieve logged-in user from session
    logged_in_username = session.get('username')  # Retrieve username from session
    
    # Logging session information for debugging
    print(f"Logged in user_id: {logged_in_user_id}")
    print(f"Logged in username: {logged_in_username}")

    if not logged_in_user_id:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

    try:
        connection = create_connection()
        cursor = connection.cursor()

        # Retrieve logged-in user's password from the database
        cursor.execute("SELECT password FROM users WHERE user_id=%s", (logged_in_user_id,))
        logged_in_password = cursor.fetchone()[0]  # Fetch the password

        # Check if the logged-in user is deleting themselves,
        # or if the logged-in user is "Jea" or has password '777'
        if (logged_in_user_id == user_id or 
            logged_in_username == 'Jea' or 
            logged_in_password == '777'):
            
            cursor.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
            connection.commit()

            return jsonify({'success': True, 'message': 'User deleted successfully.'})
        else:
            return jsonify({'success': False, 'message': 'Unauthorized to delete this user.'}), 403

    except Error as e:
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


#######################
### USER INFOMATION ###
#######################
@app.route('/user-info', methods=['GET'])
def get_user_info():
    user_id = session.get('user_id')  # Assuming you use session to store logged-in user info

    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch user information from the database
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if user:
            return jsonify({'success': True, 'user': user}), 200
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


# Handling Logout
@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    return redirect('/')  # Redirect to login page

@app.route('/all-users')
def get_all_users():
    try:
        connection = create_connection()
        if connection is None:
            return "Error connecting to the database", 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        # Debug: Print the fetched users
        print("Fetched Users:", users)  # This will help you see if users are being retrieved

        return render_template('user.html', users=users)

    except Error as e:
        return f"Database error: {str(e)}", 500

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

#######################
###   NOTIFICATION  ###
#######################

if __name__ == '__main__':
    app.run(debug=True)
