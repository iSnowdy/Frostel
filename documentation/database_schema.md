# Frostel Booking System - Database Documentation

## 📋 Overview

**Frostel** is a hotel and flight booking platform database designed to handle:
- Hotel room reservations
- Flight bookings
- Payment processing
- User reviews and wishlists
- Discount management
- Audit logging

**Database:** MySQL 8.0+  
**Character Set:** UTF8MB4 (supports emojis and international characters)  
**Schema Name:** `frostel_db`

---

## 🏗️ Architecture Overview

The database is organized into **6 main functional areas**:

1. **User Management** - Customer accounts and profiles
2. **Hotel System** - Hotels, rooms, and reservations
3. **Flight System** - Airlines, airports, flights, and bookings
4. **Payment System** - Transactions and financial records
5. **Discount & Marketing** - Promotions, reviews, and wishlists
6. **System Management** - Audit logs and automated maintenance

---

## 👥 1. User Management

### `user`
The core customer table storing user accounts.

**Key Fields:**
- `id` - Unique user identifier
- `email` - Login credential (unique)
- `password` - Hashed password
- `membership` - Loyalty tier: FREE, BRONZE, GOLD, PLATINUM

**What you'll find here:**
- Regular customers who book hotels and flights
- User profile information (name, date of birth)
- Membership level for loyalty programs

---

## 🏨 2. Hotel System

The hotel system uses a **3-level hierarchy** to manage rooms properly:

```
Hotel → Room Type → Physical Room → Reservation
```

### `hotel`
The parent table for all hotel properties.

**Key Fields:**
- `name` - Hotel name ("Grand Plaza Hotel")
- `city`, `country` - Location for searching
- `star_rating` - Quality rating (1-5 stars)
- `description` - Marketing copy about the hotel

**What you'll find here:**
- Each hotel property in the system
- Basic location and branding information
- Star ratings for filtering search results

---

### `hotel_contact_information`
Contact details for each hotel (phones, emails).

**Relationship:** Many-to-one with `hotel`
- One hotel can have multiple contact numbers (reservations, support, main desk)

**Why separate table?**
Hotels often have multiple phone numbers and email addresses. Keeping them in a separate table prevents repeating hotel data.

---

### `room_type`
Defines the **categories** of rooms a hotel offers.

**Key Fields:**
- `hotel_id` - Which hotel owns this room type
- `name` - Marketing name ("Deluxe Ocean View Suite")
- `type_category` - Standard category: SINGLE, DOUBLE, TRIPLE, QUAD
- `base_price` - Standard nightly rate
- `max_occupancy` - Maximum number of guests
- `amenities` - JSON field storing features like ["WiFi", "Mini-bar", "Ocean View"]

**What you'll find here:**
- "Deluxe Ocean View Suite" - $299/night, sleeps 2
- "Standard Single Room" - $99/night, sleeps 1
- "Family Quad Room" - $189/night, sleeps 4

**Example:**
```
Grand Plaza Hotel has 3 room types:
- Standard Single (10 physical rooms)
- Deluxe Double (20 physical rooms)
- Presidential Suite (2 physical rooms)
```

---

### `room`
The actual **physical room inventory**.

**Key Fields:**
- `hotel_id` - Which hotel
- `room_type_id` - What kind of room this is
- `room_number` - Physical identifier ("101", "A-505")
- `room_status` - Current state: AVAILABLE, OCCUPIED, RESERVED, MAINTENANCE, CLEANING

**What you'll find here:**
- Actual rooms you can book: Room 101, Room 102, Room 103...
- Each room is a specific type (Room 101 is a "Standard Single")
- Current availability status

**Why separate from room_type?**
- We need to track individual room status (Room 101 is being cleaned, Room 102 is occupied)
- Prevents double-booking the same physical room
- Allows maintenance scheduling per room

---

### `reservation`
The booking record when someone reserves a hotel room.

**Key Fields:**
- `booking_reference` - Unique confirmation code
- `user_id` - Who made the booking
- `hotel_id`, `room_id`, `room_type_id` - What was booked
- `check_in_date`, `check_out_date` - Stay duration
- `total_nights` - Auto-calculated from dates
- `base_price` - Original price
- `discount_amount` - Any discounts applied
- `total_price` - Final amount charged
- `status` - Booking lifecycle: PENDING → CONFIRMED → CHECKED_IN → CHECKED_OUT (or CANCELLED)

**What you'll find here:**
- Every hotel reservation in the system
- Past, current, and future bookings
- Cancelled bookings (kept for history)

**Status Flow:**
```
PENDING (created but not paid)
    ↓ (payment successful)
CONFIRMED (paid, waiting for check-in date)
    ↓ (guest arrives)
CHECKED_IN (guest is staying)
    ↓ (guest leaves)
CHECKED_OUT (stay complete)

    OR at any time → CANCELLED
```

**Important Notes:**
- `booking_reference` is what users use to look up their reservation
- `total_nights` is automatically calculated (you can't insert it)
- Can be cancelled at any time (status becomes CANCELLED)
- Links to both `room_id` (specific room) and `room_type_id` (for reporting)

---

## ✈️ 3. Flight System

The flight system uses a **route + instance** pattern:

```
Airline + Airport → Flight Route → Flight Instance → Flight Class → Flight Booking
```

### `airport`
All airports where flights can depart/arrive.

**Key Fields:**
- `code` - IATA code ("JFK", "MAD", "LHR")
- `name` - Full name ("John F. Kennedy International")
- `city`, `country` - Location

**What you'll find here:**
- Major international airports
- Codes for easy reference
- Used for flight origin/destination lookups

**Example:**
```
JFK - John F. Kennedy International - New York, USA
MAD - Adolfo Suárez Madrid-Barajas - Madrid, Spain
LHR - London Heathrow - London, UK
```

---

### `airline`
Airlines operating flights.

**Key Fields:**
- `code` - Airline code ("AA", "DL", "BA")
- `name` - Full airline name ("American Airlines")
- `logo_url` - For displaying in UI

**What you'll find here:**
- Major airlines (American Airlines, Delta, British Airways)
- Airline branding information
- Used to identify who operates each flight

---

### `flight_route`
The **template** for recurring flights.

**Key Fields:**
- `airline_id` - Which airline operates this route
- `flight_number` - Flight identifier ("AA1234")
- `origin_airport_id` → `destination_airport_id` - Where it flies
- `duration_minutes` - Typical flight time
- `aircraft` - Plane type ("Boeing 737")

**What you'll find here:**
- Recurring flight routes (e.g., "AA1234 flies JFK→LAX daily")
- NOT specific dates/times (those are in `flight` table)
- Route information that doesn't change day-to-day

**Why separate from flight?**
A flight route is a **pattern**: "American Airlines flight AA1234 goes from New York to Los Angeles and takes 6 hours."

The actual flights are **instances** of that pattern:
- AA1234 on Dec 20 at 8:00 AM
- AA1234 on Dec 21 at 8:00 AM
- AA1234 on Dec 22 at 8:00 AM

This separation prevents repeating airline, origin, destination, etc. for every single flight.

---

### `flight`
A **specific departure** of a flight route.

**Key Fields:**
- `flight_route_id` - Which route this flight follows
- `departure_datetime` - Exact departure time
- `arrival_datetime` - Expected arrival time
- `status` - Current state: SCHEDULED, BOARDING, DEPARTED, ARRIVED, DELAYED, CANCELLED
- `gate`, `terminal` - Airport logistics

**What you'll find here:**
- Specific flights you can book: "AA1234 departing Dec 20 at 8:00 AM"
- Real-time status updates
- Gate and terminal assignments

**Example:**
```
Flight Route: AA1234 (JFK → LAX)

Flight Instances:
- Dec 20, 8:00 AM → 11:30 AM (SCHEDULED)
- Dec 21, 8:00 AM → 11:30 AM (SCHEDULED)
- Dec 22, 8:00 AM → 11:45 AM (DELAYED)
```

---

### `flight_class`
Seat classes and availability for each flight.

**Key Fields:**
- `flight_id` - Which specific flight
- `class_type` - ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
- `total_seats` - How many seats in this class
- `available_seats` - How many are still bookable
- `base_price` - Price for this class
- `baggage_allowance_kg` - Weight limit

**What you'll find here:**
- One flight has multiple classes (Economy, Business, First)
- Each class has different pricing and availability
- Real-time seat availability

**Example:**
```
Flight AA1234 on Dec 20:
- Economy: 150 seats, 42 available, $299
- Business: 30 seats, 12 available, $899
- First Class: 12 seats, 4 available, $1,999
```

**Why separate from flight?**
- Same flight has multiple price tiers
- Each class has independent availability
- Allows flexible pricing per class

---

### `flight_booking`
The booking record when someone books a flight.

**Key Fields:**
- `booking_reference` - Unique confirmation ("FLT-251120-XYZ789")
- `user_id` - Who made the booking
- `flight_id` - Which specific flight
- `flight_class_id` - Which class (Economy/Business/First)
- `passenger_name`, `passenger_email` - Traveler details (might be gift)
- `seat_number` - Assigned seat ("12A")
- `total_price` - Amount paid
- `status` - PENDING → CONFIRMED → CHECKED_IN → BOARDED → COMPLETED (or CANCELLED)

**What you'll find here:**
- Every flight booking in the system
- Passenger information (can differ from user making booking)
- Seat assignments

**Status Flow:**
```
PENDING (created but not paid)
    ↓
CONFIRMED (paid, ticket issued)
    ↓
CHECKED_IN (online/airport check-in complete)
    ↓
BOARDED (passenger on plane)
    ↓
COMPLETED (flight arrived)

    OR at any time → CANCELLED
```

---

## 💳 4. Payment System

### `payment`
Financial transactions for bookings.

**Key Fields:**
- `payment_reference` - Unique payment ID ("PAY-251120-ABC123")
- `user_id` - Who paid
- `booking_id` OR `flight_booking_id` - What was paid for
- `booking_type` - HOTEL, FLIGHT, or PACKAGE (both)
- `subtotal`, `discount_amount`, `total_amount` - Price breakdown
- `payment_processor` - STRIPE, PAYPAL, BANK, etc.
- `processor_transaction_id` - External payment gateway ID
- `status` - PENDING → COMPLETED (or FAILED, REFUNDED)

**What you'll find here:**
- Every payment transaction
- Links to Stripe/PayPal transaction IDs
- Payment status for reconciliation

**Important Constraints:**
The database enforces that:
- If `booking_type = 'HOTEL'`, then `booking_id` must be set
- If `booking_type = 'FLIGHT'`, then `flight_booking_id` must be set
- If `booking_type = 'PACKAGE'`, both must be set

**Why link to bookings?**
- Track what each payment was for
- Support refunds (know what to refund)
- Financial reporting (hotel revenue vs flight revenue)

---

## 🎁 5. Discount & Marketing

### `discount`
Promotional offers and discounts.

**Key Fields:**
- `name` - Discount name ("Summer Sale 2025")
- `description` - Marketing copy
- `discount_percentage` - How much off (0-100%)
- `applicable_to` - HOTEL or FLIGHT
- `start_date`, `end_date` - Validity period
- `is_active` - Whether discount is currently active

**What you'll find here:**
- Active promotions ("20% off all beach hotels")
- Seasonal sales
- Limited-time offers

---

### `hotel_discount` & `flight_discount`
Junction tables linking discounts to specific hotels/flights.

**Purpose:**
A discount can apply to multiple hotels, and a hotel can have multiple discounts.

**Example:**
```
"Summer Sale" discount applies to:
- Grand Plaza Hotel (Miami)
- Beach Resort Hotel (Cancun)
- Ocean View Hotel (Malibu)
```

**How it works:**
```sql
-- Create discount
INSERT INTO discount (name, discount_percentage, applicable_to)
VALUES ('Summer Sale', 20.00, 'HOTEL');

-- Apply to multiple hotels
INSERT INTO hotel_discount (hotel_id, discount_id)
VALUES 
    (1, 1),  -- Grand Plaza
    (2, 1),  -- Beach Resort
    (3, 1);  -- Ocean View
```

---

### `review`
User reviews for hotels and flights.

**Key Fields:**
- `user_id` - Who wrote the review
- `review_type` - HOTEL or FLIGHT
- `hotel_id` OR `flight_id` - What's being reviewed
- `rating` - 1-5 stars
- `title`, `comment` - Review content
- `is_verified`, `is_approved` - Moderation flags
- `helpful_count` - How many users found it helpful

**What you'll find here:**
- Customer reviews and ratings
- Both approved and pending reviews
- Verified purchase reviews (user actually stayed/flew)

**Verification:**
Reviews marked `is_verified = TRUE` come from users who actually booked and completed their stay/flight.

---

### `wishlist_hotel` & `wishlist_flight`
User's saved hotels and flights for future booking.

**Key Fields:**
- `user_id` - Whose wishlist
- `hotel_id` OR `flight_route_id` - What they saved
- `notes` - Personal notes ("For anniversary trip")
- `created_at` - When they saved it

**What you'll find here:**
- Hotels users want to book later
- Flight routes users are watching
- Personal trip planning notes

**Why two tables?**
Hotels and flights are different entities, so separate wishlists keep it clean.

---

## 🔍 6. System Management

### `audit_log`
Complete history of all changes to critical tables.

**Key Fields:**
- `table_name` - Which table was changed ('reservation', 'payment', 'user')
- `operation` - INSERT, UPDATE, or DELETE
- `record_id` - ID of the affected record
- `user_id` - Who made the change
- `old_values`, `new_values` - JSON of what changed
- `created_at` - When it happened

**What you'll find here:**
- Every booking creation, modification, cancellation
- Every payment transaction
- Every user account change
- Complete change history for debugging and compliance

**Example Entry:**
```json
{
  "table_name": "reservation",
  "operation": "UPDATE",
  "record_id": 123,
  "user_id": 5,
  "old_values": {"status": "CONFIRMED"},
  "new_values": {"status": "CANCELLED"},
  "created_at": "2025-11-02 14:30:00"
}
```

**Use Cases:**
- "Who cancelled booking #123?"
- "Show me all changes to payment #456"
- "What did user #5 do today?"
- "How many bookings were cancelled this month?"

---

## 🤖 Automated Systems

### Triggers (Automatic Audit Logging)

The database has **9 triggers** that automatically log changes:

**For Reservations:**
- `reservation_audit_insert` - Logs new bookings
- `reservation_audit_update` - Logs changes (cancellations, modifications)
- `reservation_audit_delete` - Logs deletions

**For Flight Bookings:**
- `flight_booking_audit_insert`
- `flight_booking_audit_update`
- `flight_booking_audit_delete`

**For Payments:**
- `payment_audit_insert`
- `payment_audit_update`
- `payment_audit_delete`

**How they work:**
Every time you INSERT, UPDATE, or DELETE a record in these tables, the trigger automatically creates an audit log entry. **No application code needed.**

**Example:**
```sql
-- You run this:
UPDATE reservation SET status = 'CANCELLED' WHERE id = 123;

-- Trigger automatically does this:
INSERT INTO audit_log (table_name, operation, record_id, old_values, new_values)
VALUES ('reservation', 'UPDATE', 123, 
    '{"status": "CONFIRMED"}', 
    '{"status": "CANCELLED"}'
);
```

---

### Events (Scheduled Maintenance)

The database has **3 automated events** that run on schedules:

#### 1. `cancel_expired_pending_bookings`
- **Runs:** Every 1 hour
- **Purpose:** Cancel bookings that have been PENDING for more than 24 hours
- **Why:** Users create bookings but don't complete payment, blocking inventory

**What it does:**
```sql
-- Finds reservations and flight bookings that are:
-- - Status = PENDING
-- - Created more than 24 hours ago
-- → Changes their status to CANCELLED
```

**Example:**
```
10:00 AM - User creates booking, status = PENDING
10:30 AM - User closes browser without paying
11:00 AM - Event runs, booking still PENDING (not 24h yet)
...
Next day 11:00 AM - Event runs, sees booking is 25h old → Cancels it
```

---

#### 2. `expire_old_discounts`
- **Runs:** Every day at 3:00 AM
- **Purpose:** Deactivate discounts that have passed their end date
- **Why:** Clean up expired promotions automatically

**What it does:**
```sql
-- Finds discounts where:
-- - end_date has passed
-- - is_active = TRUE
-- → Sets is_active = FALSE
```

**Example:**
```
"Summer Sale" discount:
- end_date: 2025-08-31
- is_active: TRUE

Sept 1, 3:00 AM - Event runs
→ Sets is_active = FALSE
→ Discount no longer applies to new bookings
```

---

#### 3. `cleanup_old_audit_logs`
- **Runs:** Every week at 3:00 AM
- **Purpose:** Delete audit logs older than 1 year
- **Why:** Prevent audit table from growing infinitely

**What it does:**
```sql
-- Deletes audit_log entries where:
-- - created_at is older than 1 year
```

**Retention Policy:**
- Keep audit logs for 1 year (compliance, debugging)
- After 1 year, delete them (free up space)

**Note:** In production, you might want to **archive** instead of delete (move to cold storage).

---

## 🔗 Key Relationships

### Many-to-One Relationships

**One hotel has many rooms:**
```
hotel (1) ─── (many) room
```

**One room type has many physical rooms:**
```
room_type (1) ─── (many) room
```

**One user has many reservations:**
```
user (1) ─── (many) reservation
```

**One hotel has many reservations:**
```
hotel (1) ─── (many) reservation
```

**One flight has many bookings:**
```
flight (1) ─── (many) flight_booking
```

---

### Many-to-Many Relationships

**Hotels ↔ Discounts** (via `hotel_discount`):
```
hotel (many) ─── hotel_discount ─── (many) discount
```
One discount can apply to many hotels, and one hotel can have many discounts.

**Flights ↔ Discounts** (via `flight_discount`):
```
flight (many) ─── flight_discount ─── (many) discount
```

**Users ↔ Hotels** (via `wishlist_hotel`):
```
user (many) ─── wishlist_hotel ─── (many) hotel
```
Users can save many hotels to wishlist, and hotels can be in many wishlists.

---

## 📊 Data Flow Examples

### Example 1: Booking a Hotel Room

1. **User searches** for hotels in Madrid
   ```sql
   SELECT * FROM hotel WHERE city = 'Madrid'
   ```

2. **System shows available room types**
   ```sql
   SELECT rt.* FROM room_type rt
   WHERE rt.hotel_id = 5
   ```

3. **User selects "Deluxe Double" room**
   - System finds available physical rooms of that type
   ```sql
   SELECT r.* FROM room r
   WHERE r.room_type_id = 10
     AND r.room_status = 'AVAILABLE'
   ```

4. **User completes booking**
   ```sql
   INSERT INTO reservation (user_id, hotel_id, room_id, room_type_id, 
                            check_in_date, check_out_date, total_price, status)
   VALUES (5, 5, 101, 10, '2025-12-20', '2025-12-25', 500.00, 'PENDING')
   ```
   - **Trigger fires:** `reservation_audit_insert` logs the new booking

5. **User pays**
   ```sql
   INSERT INTO payment (user_id, booking_id, booking_type, total_amount, status)
   VALUES (5, 123, 'HOTEL', 500.00, 'COMPLETED')
   ```
   - **Trigger fires:** `payment_audit_insert` logs the payment

6. **System confirms booking**
   ```sql
   UPDATE reservation SET status = 'CONFIRMED' WHERE id = 123
   ```
   - **Trigger fires:** `reservation_audit_update` logs the status change

---

### Example 2: Expired Booking Cleanup

**Timeline:**
- **10:00 AM Monday:** User creates booking (status = PENDING)
- **11:00 AM Monday:** Event `cancel_expired_pending_bookings` runs (booking is 1h old, nothing happens)
- **User never pays...**
- **11:00 AM Tuesday:** Event runs again (booking is 25h old)
  - Status changes: PENDING → CANCELLED
  - Room becomes available again
  - **Trigger fires:** `reservation_audit_update` logs the cancellation

---

### Example 3: Applying a Discount

**Setup:**
```sql
-- Create "Black Friday" discount
INSERT INTO discount (name, discount_percentage, applicable_to, start_date, end_date)
VALUES ('Black Friday Sale', 25.00, 'HOTEL', '2025-11-25', '2025-11-30');

-- Apply to specific hotels
INSERT INTO hotel_discount (hotel_id, discount_id)
VALUES (1, 1), (2, 1), (3, 1);
```

**When user books:**
```sql
-- Application calculates discount
base_price = 500.00
discount = 500.00 * 0.25 = 125.00
total_price = 500.00 - 125.00 = 375.00

INSERT INTO reservation (..., base_price, discount_amount, total_price)
VALUES (..., 500.00, 125.00, 375.00)
```

**After Nov 30:**
- Event `expire_old_discounts` runs daily
- Sets `is_active = FALSE` for expired discounts
- New bookings no longer get the discount

---

## 🛡️ Data Integrity Features

### Constraints That Protect Your Data

**Check Constraints:**
- ✅ Check-out date must be after check-in date
- ✅ Star rating must be 1-5
- ✅ Number of guests must be > 0
- ✅ Discount percentage must be 0-100
- ✅ Payment must link to correct booking type

**Foreign Key Constraints:**
- ✅ Can't create reservation without valid user, hotel, room
- ✅ Can't delete hotel if it has active reservations (RESTRICT)
- ✅ If room type is deleted, its rooms are also deleted (CASCADE)

**Unique Constraints:**
- ✅ Email addresses must be unique
- ✅ Booking references must be unique
- ✅ Airport codes must be unique (JFK, LAX, etc.)

**Generated Columns:**
- ✅ `total_nights` is automatically calculated from dates
- ✅ Can't be manually set (database calculates it)

---

## 🎯 Performance Considerations

### Indexes

The database has indexes strategically placed on:

**Foreign Keys:** Every foreign key has an index (required for performance)

**Search Columns:**
- `hotel.city`, `hotel.country` - For location searches
- `user.email` - For login lookups
- `reservation.check_in_date` - For date range queries

**Status Columns:**
- `reservation.status` - For filtering active bookings
- `flight.status` - For showing available flights

**Reference Codes:**
- `reservation.booking_reference` - For confirmation lookup
- `airport.code` - For flight searches

### Query Optimization

**Good Queries (Use Indexes):**
```sql
-- Uses idx_city
SELECT * FROM hotel WHERE city = 'Madrid'

-- Uses idx_check_in_date
SELECT * FROM reservation WHERE check_in_date >= '2025-12-20'

-- Uses unique_email (unique constraint creates index)
SELECT * FROM user WHERE email = 'user@example.com'
```

**Queries to Avoid:**
```sql
-- No index on name (but there is!)
SELECT * FROM user WHERE name LIKE '%John%'

-- Function on indexed column (can't use index)
SELECT * FROM reservation WHERE YEAR(check_in_date) = 2025
```

---

## 📝 Common Queries

### Find Available Rooms
```sql
SELECT h.name, rt.name, rt.base_price
FROM hotel h
JOIN room_type rt ON h.id = rt.hotel_id
WHERE h.city = 'Madrid'
  AND EXISTS (
    SELECT 1 FROM room r
    WHERE r.room_type_id = rt.id
      AND r.room_status = 'AVAILABLE'
  )
```

### User's Booking History
```sql
SELECT 
    r.booking_reference,
    h.name as hotel_name,
    r.check_in_date,
    r.check_out_date,
    r.total_price,
    r.status
FROM reservation r
JOIN hotel h ON r.hotel_id = h.id
WHERE r.user_id = 5
ORDER BY r.check_in_date DESC
```

### Hotel Average Rating
```sql
SELECT 
    h.name,
    AVG(rv.rating) as avg_rating,
    COUNT(rv.id) as review_count
FROM hotel h
LEFT JOIN review rv ON h.id = rv.hotel_id AND rv.review_type = 'HOTEL'
WHERE rv.is_approved = TRUE
GROUP BY h.id, h.name
```

### Revenue Report
```sql
SELECT 
    DATE(p.created_at) as date,
    COUNT(*) as transactions,
    SUM(p.total_amount) as revenue
FROM payment p
WHERE p.status = 'COMPLETED'
  AND p.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(p.created_at)
ORDER BY date DESC
```

### Cancelled Bookings (From Audit Log)
```sql
SELECT 
    record_id as booking_id,
    user_id,
    old_values->>'$.status' as old_status,
    new_values->>'$.status' as new_status,
    created_at as cancelled_at
FROM audit_log
WHERE table_name = 'reservation'
  AND operation = 'UPDATE'
  AND new_values->>'$.status' = 'CANCELLED'
  AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
```

---

*Last Updated: November 2025*  
*Database Version: 1.0*  
*MySQL Version: 8.0+*