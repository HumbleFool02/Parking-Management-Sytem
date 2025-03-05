from flask import Flask, render_template, Response , request, send_from_directory, redirect, url_for, flash, session, jsonify
import  json, uuid
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta, date, time
from random import choice
from sqlalchemy import func

with open('config.json', 'r') as c:
    params = json.load(c)["params"]

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# Configure the SQLite database
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/skynet/Repositories/ParkEazy/database/parking_slot.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/parkeasy'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
bcrypt = Bcrypt(app)


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.String(10), primary_key=False, unique= True, nullable = False )
    name = db.Column(db.String(100), primary_key=False, nullable = False )
    privilege = db.Column(db.String(3), primary_key=False, nullable = False )
    username = db.Column(db.String(100), primary_key=False, nullable = False , unique = True)
    password = db.Column(db.String(1000), primary_key=False)

    def is_authenticated(self):
        return True  

    def is_active(self):
        return True  

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    
class slotStatus(db.Model):
    __tablename__ = 'slotStatus'
    slot = db.Column(db.Integer, primary_key=True, nullable = False , unique = True, )
    status = db.Column(db.String(20), primary_key=False)


class sessionStatus(db.Model):
    __tablename__ = 'sessionStatus'
    id = db.Column(db.String(4), primary_key = True)
    user_id = db.Column(db.String(10), primary_key=True, nullable = False , unique = True)
    login = db.Column(db.String(20), primary_key=False)
    logout = db.Column(db.String(20), primary_key=False)

class bookStatus(db.Model):
    __tablename__ = 'bookStatus'
    booking_id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.String, primary_key=True, nullable = False , unique = True)
    booking_dt = db.Column(db.String(20), primary_key=False)
    slot = db.Column(db.Integer, primary_key=False)
    start_time =db.Column(db.String(20), primary_key=False)
    end_time =db.Column(db.String(20), primary_key=False)
    duration = db.Column(db.String(20), primary_key=False)

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, )
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    license = db.Column(db.String(20))

class VehicleDatabase(db.Model):
    __tablename__ = 'vehicleDatabase'
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    variant = db.Column(db.String(50))

class alerts(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    date_time = db.Column(db.String(50))
    alert = db.Column(db.String(50))

def serialize_datetime(dt):
    if isinstance(dt, datetime):
        return dt.isoformat()
    return None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            print("success")
            flash('Login successful!', 'success')
            login_time = datetime.now()

            while True:
                session_id = str(uuid.uuid4())[:4]
                existing_session = sessionStatus.query.filter_by( id= session_id).first()
                if not existing_session:
                    break
            
            record = sessionStatus(id = session_id, user_id = user.user_id ,login = login_time )
            db.session.add(record)
            db.session.commit()
            session['session_id'] = record.id
            session['user_id'] = user.user_id
            print(user.privilege)
            if user.privilege == "USR":
                return redirect(url_for('user_dashboard'))
            elif user.privilege == 'MNG':
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid privilege level.', 'danger')
        
        else:
            print("unsuc")
            flash(error_message, 'danger')
            error_message = 'Login failed. Check your username and password.'

    return render_template('login.html', params = params, error_message=error_message)

@app.route('/logout')
@login_required
def logout():
    logout_time = datetime.now()
    session_id = session.get('session_id')
    
    if session_id:
        record = sessionStatus.query.filter_by( id= session_id).first()
        if record:
            record.logout = logout_time
            db.session.commit()
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    slotstatus = slotStatus.query.filter_by().all()
    occupied_slots = slotStatus.query.filter(slotStatus.status == 'Empty').count()
    empty_slots = slotStatus.query.filter(slotStatus.status == 'Filled').count()
    total_slots = occupied_slots + empty_slots
    occupancy_percentage = round(occupied_slots * 100 /total_slots,2)
    current_date = datetime.now().date()
    bookings = bookStatus.query.filter(func.date(bookStatus.booking_dt) == current_date).all()
        
    return render_template('dashboard.html' , slot_statuses = slotstatus, total_slots = total_slots, empty_slots = empty_slots, name = current_user.name, occupied_slots = occupied_slots, occupancy_percentage =occupancy_percentage, params = params, bookings = bookings)

@app.route('/refresh', methods=['GET'])
def refresh_parking_lot_overview():
    slotstatus = slotStatus.query.filter_by().all()

    slot_statuses = []
    for slot in slotstatus:
        slot_data = {
            'slot': slot.slot,
            'status': slot.status
        }
        slot_statuses.append(slot_data)

    occupied_slots = slotStatus.query.filter(slotStatus.status == 'Filled').count()
    empty_slots = slotStatus.query.filter(slotStatus.status == 'Empty').count()
    total_slots = occupied_slots + empty_slots
    occupancy_percentage = round(occupied_slots * 100 / total_slots, 2)

    last_updated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'slot_statuses': slot_statuses,
        'total_slots': total_slots,
        'empty_slots': empty_slots,
        'occupied_slots': occupied_slots,
        'occupancy_percentage': occupancy_percentage,
        'last_updated_time': last_updated_time  
    })

@app.route('/get_user_vehicles/<user_id>')
@login_required
def get_user_vehicles(user_id):
    try:
        # Query the Vehicle table to find vehicles associated with the specified user ID
        vehicles = Vehicle.query.filter_by(user_id=user_id).all()

        # Serialize vehicles to JSON format
        serialized_vehicles = []
        for vehicle in vehicles:
            serialized_vehicle = {
                'serialNo': vehicle.id,  # Assuming each vehicle has a unique serial number
                'make': vehicle.make,
                'model': vehicle.model,
                'license': vehicle.license
            }
            serialized_vehicles.append(serialized_vehicle)

        return jsonify(serialized_vehicles)

    except Exception as e:
        print(f"Error fetching user vehicles: {e}")
        return jsonify({'error': 'Failed to fetch user vehicles'}), 500

@app.route('/get_users')
@login_required
def get_users():
    try:
        # Query all users from the User table
        users = User.query.filter_by(privilege = 'USR').all()
        
        # Serialize users to JSON format
        serialized_users = [{'id': user.user_id, 'name': user.name} for user in users]
        
        return jsonify(serialized_users)
    
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500


@app.route('/get_makes', methods=['GET'])
def get_makes():
    try:
        # Fetch distinct makes from the vehicleDatabase table
        makes = db.session.query(VehicleDatabase.make).distinct().all()
        makes = [make[0] for make in makes]
        return jsonify(makes)
    except Exception as e:
        print(f"Error fetching makes: {e}")
        return jsonify([])

@app.route('/get_models', methods=['POST'])
def get_models():
    try:
        make = request.form.get('make')
        # Fetch models based on the selected make from the vehicleDatabase table
        models = VehicleDatabase.query.filter_by(make=make).with_entities(VehicleDatabase.model).distinct().all()
        models = [model.model for model in models]
        print(models)
        return jsonify(models)
    except Exception as e:
        print(f"Error fetching models: {e}")
        return jsonify([])

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    user_id = session.get('user_id')

    if user_id:
        bookings = bookStatus.query.filter_by(user_id=user_id).all()

        return render_template('user_dashboard.html', bookings=bookings, name = current_user.name, params = params)
    else:
        return redirect('/login')

@app.route('/book_slot', methods=['POST'])
def book_slot():
    try:
        user_id = session.get('user_id')
        booking_dt = datetime.now()
        start_time = request.json.get('startTime')
        duration = int(request.json.get('duration'))  

        if not user_id or not start_time or duration <= 0:
            return jsonify({'success': False, 'message': 'Invalid form data'}), 400
        
        # Calculate end time based on start time and duration
        end_time = (datetime.strptime(start_time, '%H:%M') + timedelta(minutes=duration)).strftime('%H:%M')

        # Get all slots from the slotStatus table
        all_slots = slotStatus.query.all()
        
        # Initialize a list to store available slots
        available_slots = []

        # Check each slot for overlapping bookings
        for slot in all_slots:
            is_available = True
            
            # Get existing bookings for the slot within the requested time range
            existing_bookings = bookStatus.query.filter(
                bookStatus.slot == slot.slot,
                bookStatus.start_time < end_time,
                bookStatus.end_time > start_time
            ).all()
            
            # If there are overlapping bookings, mark the slot as unavailable
            if existing_bookings:
                is_available = False
            
            # Add the slot to the list of available slots if it's available
            if is_available:
                available_slots.append(slot.slot)
        
        # If there are no available slots, return a message indicating unavailability
        if not available_slots:
            return jsonify({'success': False, 'message': 'No available slots at the requested time'}), 400
        
        # Choose a random available slot
        chosen_slot = choice(available_slots)
        
        # Assign the slot to the user and update the bookStatus table
        while True:
            booking_id = str(uuid.uuid4())[:6]
            existing_booking_id = bookStatus.query.filter_by(booking_id=booking_id).first()
            if not existing_booking_id:
                break
        
        new_booking = bookStatus(
            booking_id=booking_id,
            user_id=user_id,
            booking_dt=booking_dt,
            slot=chosen_slot,
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )
        db.session.add(new_booking)
        db.session.commit()

        response_data = {
            'booking_id': booking_id,
            'slot': chosen_slot,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error booking slot: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while processing the request'}), 500

@app.route('/add_vehicle', methods=['POST'])
@login_required
def add_vehicle():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User not logged in'}), 401

        make = request.json.get('make')
        model = request.json.get('model')
        license = request.json.get('license')

        if not make or not model or not license:
            return jsonify({'success': False, 'message': 'Incomplete form data'}), 400
        
        while True:
            vehicle_id = str(uuid.uuid4())[:6]
            existing_vehicle_id = Vehicle.query.filter_by(id=vehicle_id).first()
            if not existing_vehicle_id:
                break

        # Add the vehicle to the database
        new_vehicle = Vehicle(
            id = vehicle_id,
            user_id=user_id,
            make=make,
            model=model,
            license=license
        )
        db.session.add(new_vehicle)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Vehicle added successfully'}), 200

    except Exception as e:
        print(f"Error adding vehicle: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while adding the vehicle'}), 500

@app.route('/get_vehicles')
@login_required
def get_vehicles():
    try:
        user_id = session.get('user_id') 

        # Fetch vehicles belonging to the current user
        vehicles = Vehicle.query.filter_by(user_id=user_id).all()
        
        # Serialize vehicles to JSON format
        serialized_vehicles = []
        for vehicle in vehicles:
            serialized_vehicle = {
                'make': vehicle.make,
                'model': vehicle.model,
                'license': vehicle.license,
                'id': vehicle.id  # Assuming each vehicle has a unique ID
            }
            serialized_vehicles.append(serialized_vehicle)
        
        return jsonify(serialized_vehicles)
    
    except Exception as e:
        print(f"Error fetching vehicles: {e}")
        return jsonify({'error': 'Failed to fetch vehicles'}), 500

@app.route('/delete_vehicle/<vehicle_id>', methods=['DELETE'])
@login_required
def delete_vehicle(vehicle_id):
    try:
        # Query the Vehicle table to find the vehicle with the given ID
        vehicle = Vehicle.query.get(vehicle_id)

        # Check if the vehicle exists
        if not vehicle:
            return jsonify({'success': False, 'message': 'Vehicle not found'}), 404

        # Check if the logged-in user owns the vehicle
        if vehicle.user_id != session.get('user_id'):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        # Delete the vehicle from the database
        db.session.delete(vehicle)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Vehicle deleted successfully'})

    except Exception as e:
        print(f"Error deleting vehicle: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while deleting the vehicle'}), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        
        while True:
            user_id = str(uuid.uuid4())[:10]
            existing_user = User.query.filter_by(user_id=user_id).first()
            if not existing_user:
                break

        new_user = User(name = name, username=username, privilege = "USR", password=password, user_id = user_id)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', params = params)


if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host= '192.168.0.106', port = 5000, debug = True) #Archer C64
    #app.run(host= '192.168.0.101', port=5000, debug=True) #WR720N
    #app.run(host= '192.168.0.16', port=5000, debug=True)