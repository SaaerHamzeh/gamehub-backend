from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from decimal import Decimal

# ---------------------------------------------------------
# AUTHAUTHORIZATION & USERS
# ---------------------------------------------------------

class User(AbstractUser):
    """
    Custom user model restricted to exactly two roles as requested.
    This replaces the frontend's insecure PIN validation logic.
    """
    ROLE_CHOICES = (
        ('OWNER', 'Owner'),
        ('STAFF', 'Staff Worker'), # Combines Manager/Cashier logic into a single generic staff role
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STAFF')
    # Optional: PIN field if you want to support both standard Token login and legacy PIN login mapped to users.
    pin = models.CharField(max_length=10, unique=True, null=True, blank=True)

# ---------------------------------------------------------
# DYNAMIC RESOURCES & BUFFET
# ---------------------------------------------------------

class ResourceConfig(models.Model):
    """
    Completely generic entity supporting any type of rentable item:
    Examples: 
      - name="PC", prefix="PC", count=10
      - name="PlayStation 5", prefix="PS", count=5
      - name="Billiard Table", prefix="BLRD", count=3
      - name="Card Table", prefix="CARD", count=2
      
    Customization (JSON metadata) allows the owner to inject:
      {"vip_multiplier": 1.5, "per_controller_fee": 2.0} -> entirely arbitrary configs.
    """
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=10, help_text="e.g. PC, TBL, PS")
    count = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True, help_text="Store arbitrary resource configurations via JSON")

    def __str__(self):
        return self.name

class BuffetItem(models.Model):
    """
    Replaces CafeItem. Generic structure for snacks, drinks, physical products.
    """
    name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    metadata = models.JSONField(default=dict, blank=True, help_text="e.g., {'category': 'Hot Drinks', 'in_stock': 15}")

    def __str__(self):
        return f"{self.name} - ${self.price}"

# ---------------------------------------------------------
# CORE LOGIC: SESSIONS & TRANSACTIONS
# ---------------------------------------------------------

class Session(models.Model):
    """
    Bridging the gap: This model completely strips the client of financial authority.
    Duration, active ms, and final costs are derived exclusively from these backend values.
    """
    SESSION_TYPES = (
        ('PRE', 'Prepaid'),
        ('POST', 'Postpaid'),
    )
    
    # Session Details
    customer_name = models.CharField(max_length=200)
    resource_id = models.CharField(max_length=50, help_text="Specifies exact instance, e.g., 'PC-01' or 'CARD-02'")
    session_type = models.CharField(max_length=4, choices=SESSION_TYPES, default='POST')
    
    # Financial Params
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2)
    discount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    duration_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="For Prepaid limits")
    
    # Time Tracking (The critical components)
    start_time = models.DateTimeField(default=timezone.now)
    planned_end_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Pause Logic
    is_paused = models.BooleanField(default=False)
    last_pause_time = models.DateTimeField(null=True, blank=True)
    total_paused_ms = models.BigIntegerField(default=0)
    
    # Final Caching
    final_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    final_duration_minutes = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def get_active_ms(self, ref_time=None):
        """
        Reverse-engineered from helper.js: getActiveDurationMs.
        Prevents frontend from spoofing duration locally.
        """
        if not ref_time:
            ref_time = self.end_time if self.end_time else timezone.now()
            
        start = self.start_time
        paused_ms = self.total_paused_ms
        
        # If currently paused, we must add the time spent in the *current* pause state
        if self.is_paused and self.last_pause_time and not self.end_time:
            current_pause_duration = (ref_time - self.last_pause_time).total_seconds() * 1000
            paused_ms += int(current_pause_duration)
            
        total_ms = (ref_time - start).total_seconds() * 1000
        return max(0, total_ms - paused_ms)
        
    def get_live_cost(self, ref_time=None):
        """
        Reverse-engineered from helper.js: getLiveCost.
        Returns precise current cost ignoring what the frontend says.
        """
        active_ms = self.get_active_ms(ref_time)
        active_hours = active_ms / (1000 * 3600)
        
        rental_cost = Decimal(str(active_hours)) * Decimal(str(self.price_per_hour))
        orders_cost = sum(Decimal(str(order.price)) for order in self.orders.all())
        
        raw_total = (rental_cost + orders_cost) - Decimal(str(self.discount))
        return max(Decimal('0.00'), raw_total.quantize(Decimal('0.01')))

    def process_auto_end(self):
        """
        Lazy-evaluation logic pattern: Evaluated when sessions are queried.
        Forces the session to close if it's PRE-paid and has exceeded planned_end_time.
        Instead of a Celery background task, this ensures that no extra server resources are needed.
        """
        if not self.end_time and self.planned_end_time and not self.is_paused:
            now = timezone.now()
            if now >= self.planned_end_time:
                # Terminate accurately exactly at planned_end_time, ignoring actual 'now' latency
                self.end_session(ref_time=self.planned_end_time)

    def end_session(self, ref_time=None):
        """
        Firmly concludes the session. 
        """
        if self.end_time:
            return  # Prevent double ending
            
        ref_time = ref_time or timezone.now()
        
        # Resolve incomplete pause states before finalizing
        if self.is_paused:
            self.is_paused = False
            pause_delta = (ref_time - self.last_pause_time).total_seconds() * 1000
            self.total_paused_ms += int(pause_delta)
            
        active_ms = self.get_active_ms(ref_time)
        self.final_duration_minutes = Decimal(str(active_ms / 60000))
        self.final_cost = self.get_live_cost(ref_time)
        self.end_time = ref_time
        self.save()

    def __str__(self):
        return f"{self.resource_id} - {self.customer_name}"

class SessionOrder(models.Model):
    """
    Tracks items ordered alongside a session.
    Calculated recursively into total_cost dynamically via get_live_cost.
    """
    session = models.ForeignKey(Session, related_name='orders', on_delete=models.CASCADE)
    item_name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} -> {self.session.customer_name}"
