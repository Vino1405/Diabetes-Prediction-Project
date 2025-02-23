import os
import datetime
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_pymongo import PyMongo
import joblib
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://Vino:Vino1234@cluster1.6bvom.mongodb.net/diabetes_project_db?retryWrites=true&w=majority"
app.secret_key = 'd5bfb9f27a254ad7a05aee9c8d1560b3'
mongo = PyMongo(app)
model = joblib.load('diabetes_model.pkl')

@app.template_filter('formatdatetime')
def format_datetime(value, format='%Y-%m-%d | %I:%M:%S%p'):
    if value is None:
        return ""
    return value.strftime(format)

users_collection = mongo.db.users
patients_collection = mongo.db.patients

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('register'))
        
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash("User already exists!")
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user_data = {
            'name': name,
            'age': age,
            'email': email,
            'password': hashed_password,
            'role': 'patient'
        }
        users_collection.insert_one(user_data)
        flash("Registration successful! Please log in.")
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            flash("Logged in successfully!")
            if user['role'] == 'patient':
                target = url_for('patient_dashboard')
            elif user['role'] == 'doctor':
                target = url_for('doctor_dashboard')
            else:
                flash("Role not recognized!")
                return redirect(url_for('login'))
            return render_template('redirect.html', target=target)
        else:
            flash("Invalid email or password!") 
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'user_id' not in session or session.get('role') != 'patient':
        flash("Please log in as a patient.")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    records = list(patients_collection.find({'userid': user_id}).sort('created_datetime', -1))
    
    return render_template('patient_dashboard.html', user=user, records=records)

@app.route('/doctor_dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Please log in as a doctor.")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    
    if request.method == 'POST':
        selected_user_id = request.form.get('patient_id')
        patient_user = users_collection.find_one({'_id': ObjectId(selected_user_id)})
        if not patient_user or not patient_user.get('age'):
            flash("Patient age not found!")
            return redirect(url_for('doctor_dashboard'))
        try:
            patient_age = float(patient_user.get('age'))
        except ValueError:
            flash("Invalid age value for the patient!")
            return redirect(url_for('doctor_dashboard'))
        
        try:
            pregnancies = float(request.form.get('Pregnancies'))
            glucose = float(request.form.get('Glucose'))
            blood_pressure = float(request.form.get('BloodPressure'))
            skin_thickness = float(request.form.get('SkinThickness'))
            insulin = float(request.form.get('Insulin'))
            bmi = float(request.form.get('BMI'))
            dpf = float(request.form.get('DiabetesPedigreeFunction'))
        except Exception as e:
            flash("Invalid input data: " + str(e))
            return redirect(url_for('doctor_dashboard'))
        
        input_data = [[pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, dpf, patient_age]]
        prediction = model.predict(input_data)
        prediction_text = 'Diabetes' if prediction[0] == 1 else 'No Diabetes'
        
        current_time = datetime.datetime.now()
        patient_data = {
            'userid': selected_user_id,
            'Pregnancies': pregnancies,
            'Glucose': glucose,
            'BloodPressure': blood_pressure,
            'SkinThickness': skin_thickness,
            'Insulin': insulin,
            'BMI': bmi,
            'DiabetesPedigreeFunction': dpf,
            'Age': patient_age,
            'prediction_result': prediction_text,
            'created_datetime': current_time,
            'updated_datetime': current_time
        }
        
        patients_collection.insert_one(patient_data)
        flash("Patient data added! Prediction: " + prediction_text)
        return redirect(url_for('doctor_dashboard'))
    
    patients = list(users_collection.find({'role': 'patient'}))
    return render_template('doctor_dashboard.html', patients=patients, user=user)  # Pass the user variable


@app.route('/doctor_view_patient_select', methods=['GET', 'POST'])
def doctor_view_patient_select():
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Please log in as a doctor.")
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    # Fetch all patients for the dropdown
    patients = list(users_collection.find({'role': 'patient'}))
    
    # Initialize variables for patient data
    patient_records = None
    selected_patient = None
    
    if request.method == 'POST':
        # Get the selected patient ID from the form
        selected_patient_id = request.form.get('patient_id')
        if selected_patient_id:
            # Fetch the selected patient's details
            selected_patient = users_collection.find_one({'_id': ObjectId(selected_patient_id)})
            if selected_patient:
                # Fetch the selected patient's medical records
                patient_records = list(patients_collection.find({'userid': selected_patient_id}).sort('created_datetime', -1))
            else:
                flash("Patient not found!")
    
    return render_template('doctor_view_patient_select.html', patients=patients, patient_records=patient_records, selected_patient=selected_patient,user=user)

# View patient data in table format with Edit/Delete options.
@app.route('/doctor_view_patient/<patient_id>')
def doctor_view_patient(patient_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Please log in as a doctor.")
        return redirect(url_for('login'))
    
    # Fetch the patient's details
    user_data = users_collection.find_one({'_id': ObjectId(patient_id)})
    if not user_data:
        flash("Patient not found!")
        return redirect(url_for('doctor_dashboard'))
    
    # Fetch the patient's medical records
    patient_records = list(patients_collection.find({'userid': patient_id}).sort('created_datetime', -1))
    
    return render_template('doctor_view_patient.html', patient_records=patient_records, user=user_data)


@app.route('/edit_patient_record/<record_id>', methods=['GET', 'POST'])
def edit_patient_record(record_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Please log in as a doctor.")
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    # Fetch the record to be edited
    record = patients_collection.find_one({'_id': ObjectId(record_id)})
    if not record:
        flash("Record not found!")
        return redirect(url_for('doctor_view_patient_select'))
    
    if request.method == 'POST':
        try:
            # Get updated data from the form
            pregnancies = float(request.form.get('Pregnancies'))
            glucose = float(request.form.get('Glucose'))
            blood_pressure = float(request.form.get('BloodPressure'))
            skin_thickness = float(request.form.get('SkinThickness'))
            insulin = float(request.form.get('Insulin'))
            bmi = float(request.form.get('BMI'))
            dpf = float(request.form.get('DiabetesPedigreeFunction'))
        except Exception as e:
            flash("Invalid input: " + str(e))
            return redirect(url_for('edit_patient_record', record_id=record_id))
        
        # Fetch the patient's age from the users collection
        patient_user = users_collection.find_one({'_id': ObjectId(record['userid'])})
        try:
            patient_age = float(patient_user.get('age'))
        except Exception:
            patient_age = 0.0
        
        # Make a prediction with the updated data
        input_data = [[pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, dpf, patient_age]]
        prediction = model.predict(input_data)
        prediction_text = 'Diabetes' if prediction[0] == 1 else 'No Diabetes'
        
        # Update the record
        update_data = {
            'Pregnancies': pregnancies,
            'Glucose': glucose,
            'BloodPressure': blood_pressure,
            'SkinThickness': skin_thickness,
            'Insulin': insulin,
            'BMI': bmi,
            'DiabetesPedigreeFunction': dpf,
            'Age': patient_age,
            'prediction_result': prediction_text,
            'updated_datetime': datetime.datetime.now()
        }
        patients_collection.update_one({'_id': ObjectId(record_id)}, {"$set": update_data})
        flash("Record updated successfully!")
        return redirect(url_for('doctor_view_patient', patient_id=record['userid']))
    
    return render_template('edit_patient_record.html', record=record, user=user)

# Delete patient record.
@app.route('/delete_patient/<patient_id>', methods=['POST'])
def delete_patient(patient_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Please log in as a doctor.")
        return redirect(url_for('login'))
    # For simplicity, delete all records for the given patient.
    patients_collection.delete_many({'userid': patient_id})
    flash("Patient records deleted.")
    return redirect(url_for('doctor_dashboard'))
@app.route('/delete_patient_record/<record_id>', methods=['POST'])
def delete_patient_record(record_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Please log in as a doctor.")
        return redirect(url_for('login'))
    
    # Fetch the record to get the patient ID for redirection
    record = patients_collection.find_one({'_id': ObjectId(record_id)})
    if not record:
        flash("Record not found!")
        return redirect(url_for('doctor_view_patient_select'))
    
    # Delete the specific record
    patients_collection.delete_one({'_id': ObjectId(record_id)})
    flash("Record deleted successfully!")
    
    # Redirect back to the patient's data page
    return redirect(url_for('doctor_view_patient_select', patient_id=record['userid']))

if __name__ == '__main__':
    # Prevent duplicate default doctor creation when using Flask's debug reloader.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        if not users_collection.find_one({'email': 'doctor@example.com'}):
            default_doctor = {
                'name': 'Dr. Default',
                'age': '45',
                'email': 'doctor@example.com',
                'password': generate_password_hash('doctor123'),
                'role': 'doctor'
            }
            users_collection.insert_one(default_doctor)
            print("Default doctor account created: email: doctor@example.com, password: doctor123")
    app.run(debug=True)
