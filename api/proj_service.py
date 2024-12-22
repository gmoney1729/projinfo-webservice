from flask import Flask, request, jsonify
from pyproj import Transformer, CRS

# Initialize Flask app
app = Flask(__name__)

@app.route('/transform', methods=['GET'])
def transform_crs():
    """
    Transform coordinates from EPSG:4326 to a client-provided EPSG code.
    """
    try:
        target_epsg = request.args.get('epsg', type=int)
        if not target_epsg:
            return jsonify({"error": "Target EPSG code is required as a query parameter."}), 400

        transformer = Transformer.from_crs(4326, target_epsg)
        proj_string = transformer.to_proj4()
        crs = CRS.from_epsg(target_epsg)

        return jsonify({
            "source_epsg": 4326,
            "target_epsg": target_epsg,
            "proj4": proj_string,
            "name": crs.name,
            "datum": crs.datum.name,
            "description": transformer.description,
            "area_of_use": crs.area_of_use.name
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Entry point for Vercel
if __name__ != "__main__":
    # Allow Vercel to detect and serve the app
    app = app