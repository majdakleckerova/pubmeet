from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.db.neo4j import get_neo4j_session
import atexit

def remove_old_visits():
    """Smaže relace :VISITS starší než 6 hodin."""
    with get_neo4j_session() as session:
        session.run("""
            MATCH (u:User)-[v:VISITS]->(p:Pub) 
            WHERE v.timestamp < datetime().epochSeconds - 21600 
            DELETE v
        """)
        print("Neaktuální návštěvy byly smazány.")

scheduler = BackgroundScheduler()
scheduler.add_job(func=remove_old_visits, trigger=IntervalTrigger(minutes=10))
scheduler.start()
atexit.register(lambda: scheduler.shutdown())
