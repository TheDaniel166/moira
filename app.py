
import os
import sys
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from moira import Moira, HouseSystem

app = Flask(__name__)

# Initialize the Sovereign Engine
m = Moira()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.json
        dt_str = data.get("datetime") # ISO format
        lat = float(data.get("lat", 51.5074))
        lon = float(data.get("lon", -0.1278))
        
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # 1. Planetary Positions (Truth-First Reduction)
        chart = m.chart(dt)
        planets = {}
        for body, vessel in chart.planets.items():
            planets[body] = {
                "longitude": vessel.longitude,
                "latitude": vessel.latitude,
                "distance": vessel.distance,
                "formatted": f"{vessel.longitude:.6f}°"
            }

        # 2. House Cusps
        houses_vessel = m.houses(dt, lat=lat, lon=lon, system=HouseSystem.PLACIDUS)
        houses = [f"{c:.4f}°" for c in houses_vessel.cusps]

        # 3. Fixed Star Audit (Algol)
        star = m.fixed_star("Algol", dt)
        star_data = {
            "name": "Algol",
            "longitude": f"{star.longitude:.4f}°",
            "phase": f"{star.phase:.3f}"
        }

        return jsonify({
            "success": True,
            "planets": planets,
            "houses": houses,
            "star": star_data,
            "timestamp": dt.isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == "__main__":
    app.run(port=5000, debug=True)
