from flask import Flask, jsonify, request, make_response
import jwt
import datetime
from functools import wraps
import subprocess
import uuid
import psycopg2

# It is assumed that a table named gcpvm is already exists in the db

host = <azure database server hostname>
dbname = <database name>
user = <user name>
password = <xyz>
sslmode = "require"

# Construct connection string
conn_string = "host={0} user={1} dbname={2} password={3} sslmode={4}".format(host, user, dbname, password, sslmode)
conn = psycopg2.connect(conn_string)



app = Flask(__name__)
app.config['SECRET_KEY'] = <enter secreat key>
@app.route('dsl-translation-gcp/api/v1/login')
def Login():
    auth = request.authorization
    if auth and auth.password == <xyz> and auth.username == 'devops':
        token = jwt.encode({'user': auth.username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                           app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({'token': token})
    return make_response('wrong credentials', 401, {'WWW-Authenticate' : 'Basic realm="Login Required"'})


@app.route('dsl-translation-gcp/api/v1/healthcheck', methods=["GET"])
def Healthcheck():
    output = {
        "Status": "ok"
    }
    return jsonify(output)

def tokeRequired(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print("Auth is ", request.headers.get('Authorization'))
        try:
            tokenreq = request.headers.get('Authorization').split(" ")[1]
            print(tokenreq)
            # tokenreq = str(request.headers.get('Authorization')).removeprefix('Bearer ')
            data = jwt.decode(tokenreq, app.config['SECRET_KEY'], algorithms=['HS256', ])
        except Exception as e:
            return jsonify({'message': 'Token is missing or invalid. ' + str(e)}), 403

        return f(*args, **kwargs)
    return decorated

@app.route('dsl-translation-gcp/api/v1/test')
@tokeRequired
def Test():
    response = {'message': 'This is a valid token',
                'response': 'Hello World!'
                }
    return jsonify(response)


@app.route('dsl-translation-gcp/api/v1/createvm', methods=['POST'])
@tokeRequired
def CreateVm():
    vmName = GetUniqueName()
    requestBody = request.json
    gcpCommand = "gcloud compute instances create " + vmName + " --project=dsl-translation-embibe --zone=asia-south1-c --machine-type=e2-medium --network-interface=network-tier=PREMIUM,subnet=default --maintenance-policy=MIGRATE --service-account=339308477757-compute@developer.gserviceaccount.com --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append --create-disk=auto-delete=yes,boot=yes,device-name=instance-1,image=projects/debian-cloud/global/images/debian-10-buster-v20211209,mode=rw,size=10,type=projects/dsl-translation-embibe/zones/us-central1-a/diskTypes/pd-balanced --no-shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring --reservation-affinity=any"
    vmOutPut= subprocess.run(gcpCommand, shell=True, capture_output=True, text=True)
    print(vmOutPut.stdout, vmOutPut.returncode)
    cursor = conn.cursor()
    print(gcpCommand)
    if (vmOutPut.returncode != 0):
        failResponse = {
            'message' : 'Error Occured'
        }
        return jsonify(failResponse)

    # r = subprocess.run(
    #     "gcloud compute instances list --filter='name=" + vmName +"' --format '[tsv]'",
    #     shell=True, capture_output=True, text=True).stdout

    responseArray = vmOutPut.stdout.split("  ")

    ip = responseArray[40]
    ip2 = responseArray[42]
    command = '''INSERT INTO gcpvm (name, periodid, ip, env, state) VALUES ( '{0}', '{1}', '{2}', '{3}', {4})'''.format(vmName, str(requestBody['periodId']), str(ip), str(requestBody['envName']), True)

    cursor.execute(command)
    cursor.close()
    conn.commit()
    response = \
            {
            'message': 'Vm Created',
            'Name': vmName,
            'ip': ip
            }

    return jsonify(response)



def GetUniqueName():
    reqName = "gcp-vm-"

    return reqName + str(uuid.uuid4())



@app.route('dsl-translation-gcp/api/v1/deleteVm/<vmName>')
@tokeRequired
def DeleteVm(vmName = ""):

    gcpCommand = "gcloud compute instances delete " + str(vmName) + " --zone=asia-south1-c "
    command = ''' UPDATE gcpvm set state = 'false' where name = '{0}' '''.format(vmName)
    vmOutPut= subprocess.run(gcpCommand, shell=True, capture_output=True, text=True, input="y")
    cursor = conn.cursor()
    cursor.execute(command)
    cursor.close()
    conn.commit()

    return jsonify({"message": "VM Deleted with name " + vmName})


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
