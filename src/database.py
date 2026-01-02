
import os
from supabase import create_client, Client
from datetime import datetime, timezone

class Database:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            print("WARNING: SUPABASE_URL or SUPABASE_KEY not set. Database features will fail.")
            self.client = None
        else:
            self.client: Client = create_client(url, key)

    def add_subscription(self, label: str, user_id: str) -> bool:
        """Add a subscription. Returns True if successful, False if already exists."""
        if not self.client: return False
        try:
            # Upsert is useful, or just insert and ignore conflict
            data = {"label": label, "user_id": user_id}
            self.client.table("subscriptions").upsert(data, on_conflict="label, user_id").execute()
            return True
        except Exception as e:
            print(f"Error adding subscription {label} for {user_id}: {e}")
            return False

    def remove_subscription(self, label: str, user_id: str):
        if not self.client: return
        try:
            self.client.table("subscriptions").delete().eq("label", label).eq("user_id", user_id).execute()
        except Exception as e:
            print(f"Error removing subscription: {e}")

    def get_subscriptions(self):
        """Returns dict: {'Label': ['user_id', 'user_id']}"""
        if not self.client: return {}
        try:
            # Fetch all rows
            response = self.client.table("subscriptions").select("*").execute()
            rows = response.data
            
            # Transform to dict
            subs = {}
            for row in rows:
                lbl = row["label"]
                uid = row["user_id"]
                if lbl not in subs:
                    subs[lbl] = []
                subs[lbl].append(uid)
            return subs
        except Exception as e:
            print(f"Error fetching subscriptions: {e}")
            return {}
            
    def get_user_subscriptions(self, user_id: str):
        """Returns list of labels for a user."""
        if not self.client: return []
        try:
            response = self.client.table("subscriptions").select("label").eq("user_id", user_id).execute()
            return [row["label"] for row in response.data]
        except Exception as e:
            print(f"Error fetching user subscriptions: {e}")
            return []

    def get_notified_state(self):
        """Returns dict matching current local json format: {label: {last_notified, ...}}"""
        if not self.client: return {}
        try:
            response = self.client.table("notified_state").select("*").execute()
            state = {}
            for row in response.data:
                state[row["label"]] = row
            return state
        except Exception as e:
            print(f"Error fetching notified state: {e}")
            return {}

    def update_notified_state(self, label: str, info: dict):
        if not self.client: return
        try:
            entries = {
                "label": label,
                "last_notified": datetime.now(timezone.utc).isoformat(),
                "last_status": info.get("status_text"),
                "enrolled": info.get("enrolled")
            }
            self.client.table("notified_state").upsert(entries).execute()
        except Exception as e:
            print(f"Error updating notified state: {e}")
