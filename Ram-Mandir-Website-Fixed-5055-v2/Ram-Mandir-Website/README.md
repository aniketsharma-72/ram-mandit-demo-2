# Shri Ram Janmabhoomi Mandir — Advanced Visitor & Administration Portal

A college major-project upgrade of the original Ram Mandir visitor website.

## Technology
- Python 3 + Flask
- SQLite database
- HTML5 / CSS3 / JavaScript
- Chart.js for admin analytics
- Font Awesome icons
- Responsive mobile-first UI

## Major-project features added

### Visitor side
- User registration and secure password hashing
- User login/logout and session management
- Darshan / Aarti slot booking
- Capacity validation and duplicate-booking protection
- My Bookings with cancellation
- Live crowd-status estimate
- Festival calendar and countdown data
- Nearby places with category filtering
- Emergency contacts
- Help-desk/contact form
- Gallery lightbox
- English / Hindi switch
- Text-size accessibility control
- Scroll animations and responsive navigation
- Admin-created announcements shown on the public website

### New Admin Dashboard
Open `/admin` after administrator login.

Admin modules:
1. **Dashboard analytics**
   - Registered devotees
   - Total bookings
   - Confirmed devotees
   - Page views
   - Booking activity chart
   - Popular darshan slot analysis

2. **Booking Management**
   - Search by reference/name/email
   - Filter confirmed/cancelled bookings
   - Cancel or restore booking status
   - View devotee and slot details
   - Export complete booking data to CSV

3. **User & Role Management**
   - View registered users
   - View booking count
   - Promote visitor accounts to admin
   - Role-based authorization

4. **Darshan Slot Management**
   - Edit slot name
   - Edit start/end time
   - Change capacity
   - Changes are stored in SQLite

5. **Help Desk Inbox**
   - View visitor messages
   - Visitor email and message details

6. **Announcements**
   - Create visitor announcements
   - Choose info/warning/success type
   - Active announcement appears on the public portal

7. **Audit Log**
   - Records administrator actions such as role changes, booking status changes,
     slot updates and announcement actions.

## Demo administrator

The first database initialization creates:

- Email: `admin@rammandir.local`
- Password: `Admin@123`

**Important:** This is only a college-project demo credential. Change/remove it before any real deployment.

## Run

```bash
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5055
```

Login with the demo admin account and open **My Account → Open Admin Dashboard**, or visit:

```text
http://127.0.0.1:5055/admin
```

The SQLite database `mandir.db` is created automatically.

## Database design

Main tables:
- `users` — visitor/admin accounts
- `slots` — darshan schedules and capacities
- `bookings` — reservations
- `festivals` — festival calendar
- `places` — nearby places
- `contacts` — emergency/help numbers
- `messages` — help desk inbox
- `visits` — daily page views
- `announcements` — public notices
- `audit_logs` — administrator activity

## Important API groups

### Public / visitor
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/slots?date=YYYY-MM-DD`
- `POST /api/bookings`
- `GET /api/bookings`
- `DELETE /api/bookings/<id>`
- `GET /api/visitors/status`
- `GET /api/festivals`
- `GET /api/places`
- `GET /api/contacts`
- `POST /api/messages`
- `GET /api/announcements`
- `GET /api/stats`

### Admin
- `GET /admin`
- `GET /api/admin/overview`
- `GET /api/admin/users`
- `POST /api/admin/users/<id>/role`
- `GET /api/admin/bookings`
- `POST /api/admin/bookings/<id>/status`
- `GET /api/admin/slots`
- `POST /api/admin/slots/<id>`
- `GET /api/admin/messages`
- `GET /api/admin/audit`
- `POST /api/admin/announcements`
- `DELETE /api/admin/announcements/<id>`
- `GET /api/admin/export/bookings.csv`

## Security notes
- Passwords are hashed using Werkzeug.
- Admin APIs require a logged-in user with `role=admin`.
- Visitor accounts cannot call admin endpoints.
- Booking capacity and duplicate-booking checks happen server-side.
- Audit entries are stored in the database.
- For production, set a strong `SECRET_KEY`, use HTTPS, disable Flask debug mode,
  and run behind a production WSGI server.

## Suggested major-project presentation points

You can explain the project as:

**"Ram Mandir Digital Visitor Management & Darshan Reservation System"**

Problem:
- Visitors need one portal for schedules, reservations and visitor information.
- Administrators need a central system for bookings, capacities and visitor queries.

Solution:
- Responsive public visitor portal + role-based administration dashboard.
- SQLite-backed reservation system.
- Analytics and reporting.
- Help desk and announcement management.
- Audit trail for administrative actions.

Future scope:
- Real payment gateway
- Email/SMS booking confirmation
- QR-code ticket generation and scanning
- Government/temple-authority verified live crowd API
- Multi-admin permission levels
- Cloud database and deployment
- Hindi/English/other regional languages
