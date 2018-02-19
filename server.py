import pymysql
import time
from flask import Flask, Markup, render_template, request


def report(team_name, auton_score, driver_score, scouter_id, highest_stack, notes=''):
    # check to see if team is valid
    #c.execute("SELECT team_name FROM reports WHERE team_name='" + team_name + "'")
    #if len(c.fetchall()):
    # submit report
    date_time = int(time.time())
    c.execute('INSERT INTO '+event+'(team_name, auton_score, driver_score, highest_stack, notes, date_time, scouter_id) VALUES ("'+team_name+'",'+str(auton_score)+','+str(driver_score)+','+str(highest_stack)+',"'+notes+'",'+str(date_time)+','+str(scouter_id)+")")
    db.commit()

def pull_reports(team_name=None):
    if team_name:
        c.execute("SELECT * FROM "+event+" WHERE team_name='" + team_name + "'")
    else:
        c.execute("SELECT * FROM "+event)
    return c.fetchall()

def get_unscouted_robots(): # Returns a list of unscouted robots in string name form
	scouted = []
	unscouted = []
	for r in pull_reports():
		for t in valid_teams:
			if t == r[0] and t not in scouted:
				scouted.append(t)
	for r in valid_teams:
		if r not in scouted:
			unscouted.append(r)
	return unscouted

def compress_reports(): # Compile data and find average values for each robot
    c.execute("SELECT * FROM "+event)
    robotData = c.fetchall()
    robots = []
    for row in robotData:  # Find unique robots
        if row[0] not in robots: robots.append(row[0])
    compressedData = []
    for robot in robots:
        best_drive_score = 0
        best_auton_score = 0
        total_drive_score = 0
        total_auton_score = 0
        highest_stack = 0
        entryCount = 0
        notes = ''
        for row in robotData:
            if row[0] == robot:
                entryCount += 1
                total_drive_score += int(row[2])
                total_auton_score += int(row[1])
                if int(row[2]) > best_drive_score:
                	best_drive_score = int(row[2])
                if int(row[1]) > best_auton_score:
                	best_auton_score = int(row[1])
                if int(row[3]) > highest_stack:
                	highest_stack = int(row[3])
                if row[4]:
                	notes += '~ '+row[4]+'<br>'
        compressedData.append([robot, best_drive_score, int(total_drive_score / entryCount), best_auton_score, int(total_auton_score / entryCount), highest_stack, notes, entryCount])
    return compressedData


def robot_power(robot_stats): # Enter compiled data row as input. Formula = bestdriver + avgdriver + bestauton + avgauton + higheststack
	
	return robot_stats[1] + robot_stats[2] + robot_stats[3] + robot_stats[4] + robot_stats[5] * 2 + robot_stats[7]


def reverse_bubble_sort(collection): # Sort reports by best driver score
	length = len(collection)
	for i in range(length-1, -1, -1):#range(length-1, -1, -1)
		for j in range(i):#range(1, i)
			if robot_power(collection[j]) > robot_power(collection[j+1]):
				collection[j], collection[j+1] = collection[j+1], collection[j]
	return collection[::-1]

def retrieve_data(table):
	pass


app = Flask(__name__)

@app.route('/') # Home page
def index():
	return render_template('index.html', status="Seaquam Robotics Scouting")

@app.route('/scouting', methods=['POST', 'GET']) # Scouting submission page
def scouting():
	error = None
	if request.method == 'POST':
		auton_score = 0
		score = 0
		team_name = request.form['team'].translate(clean).upper()
		if 1==1:
		#if team_name in valid_teams:
			print("Report submitted for " + team_name)
			#Autonomous
			if request.form['auton_mobile_goal'] == "far":
				auton_score = 20
			elif request.form['auton_mobile_goal'] == "mid":
				auton_score = 10
			elif request.form['auton_mobile_goal'] == "near":
				auton_score = 5
			auton_score += int(request.form['auton_cones_stacked']) * 2
			
			if int(request.form['driver_num_mobile_mid']) + int(request.form['driver_num_mobile_near']) + (request.form.get('driver_is_mobile_far') == "yes") > 4:
				return render_template('scouting_sent.html', status=Markup('<span class="error">Error:</span> Too many mobile goals submitted. Only 4 exist.'))

			#Driver/Total
			if request.form.get('driver_is_mobile_far') == "yes":
				score += 20 + int(request.form['driver_num_cones_far']) * 2
			score += int(request.form['driver_num_mobile_mid']) * 10 + int(request.form['driver_num_cones_mid']) * 2
			score += int(request.form['driver_num_mobile_near']) * 5 + int(request.form['driver_num_cones_near']) * 2
			score += int(request.form['driver_num_cones_tower']) * 2

			highest_stack = request.form['driver_highest_stack']
			scouter_id = request.environ['REMOTE_ADDR'].translate(clean)

			report(team_name, auton_score, score, scouter_id, highest_stack, request.form['notes'].translate(sanitize))
		else:
			if len(team_name) == 0:
				team_name = "NULL"
			return render_template('scouting_sent.html', status=Markup('<span class="error">Error:</span> Invalid team name: ' + team_name + " not found in list of participating robots."))
		return render_template('index.html', status="Scouting report sent successfully")
	elif request.method == 'GET':
		return render_template('scouting.html', error=error)
	return "Error: Method type not GET or POST" #Literally impossible

@app.route('/data') # Compiled scouting reports page
def data():
	robots_data = ''
	for i, row in enumerate(reverse_bubble_sort(compress_reports())):
		robots_data += '<tr><td>'+str(i+1)+'</td>'
		for cell in row:
			robots_data += '<td>'+str(cell)+'</td>'
		robots_data +='</tr>'
	robots_data_html = Markup(robots_data)

	unscouted_robots = get_unscouted_robots()
	unscouted = ''
	if unscouted_robots:
		unscouted += '<h2>Not Yet Scouted:</h2><div class="unscouted">'
	else:
		unscouted = '<h2>All Robots Scouted</h2>'
	for r in unscouted_robots:
		unscouted += r+' '
	unscouted_html = Markup(unscouted+'</div>')

	return render_template('data.html', data=robots_data_html, unscouted=unscouted_html)

@app.route('/old_data')
def old_data():
	return render_template('old_data.html')


@app.route('/comox')
def comox():
	return render_template('comox.html')

@app.route('/mcmath')
def mcmath():
	return render_template('mcmath.html')

@app.route('/agenda')
def agenda():
	return render_template('agenda.html')


@app.errorhandler(404) #Error 404 page
def page_not_found(e):
	return render_template('404.html'), 404

if __name__ == '__main__':
	clean = str.maketrans('', '', """ ^$#@~`&;:|{()}[]<>+=!?.,\/*-_"'""")
	sanitize = str.maketrans('', '', """^$#@~`;:|{()}[]+=\*_"'""")

	# Open database connection
	db = pymysql.connect("localhost","root","geheim","vex_robotics_scouting")
	c = db.cursor()

	event = "lastchance"
	c.execute('CREATE TABLE IF NOT EXISTS '+event+'(team_name TEXT, auton_score INT, driver_score INT, highest_stack INT, notes TEXT, date_time BIGINT, scouter_id BIGINT)')
	#TODO Swap out hard-coding for scraped data stored in a database https://www.robotevents.com/robot-competitions/vex-robotics-competition/RE-VRC-17-2911.html 
	valid_teams = ['2A','2C','2E','2G','2H','2N','2X','2Y',
                   '600U','600V',
                   '1010E','1010F','1010G','1010H','1010M','1010R','1010V','1010W','1010Y','1011X',
                   '1136C',
                   '1346A','1346B','1346C',
                   '1521A','1521B',
                   '1700B',
                   '4549A','4549C',
                   '5123A',
                   '6264A','6264C','6264D',
                   '7842C','7842E','7842G','7842H','7842J','7842K','7842N',
                   '8001A',
                   '9181A','9181C','9181D',
                   '9594C','9594M','9594R',
                   '10445A','10445B',
                   '24469A',
                   '57421A',
                   '64008G',
                   '77174A',
                   '83720A',
                   '98549A','98549Y'
                   #,'TEST'
                   ] #Remove 'TEST' from list during real use

	app.run(threaded=True, debug=True, host='0.0.0.0', port=80)

db.close()
print('done')
