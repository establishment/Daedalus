var fs = require('fs'),
    https = require('https'),
    express = require('express'),
    app = express();

if (process.argv.length != 5) {
    console.log("Invalid arguments! Please run with: [domain] [path/to/privateKey.pem] [path/to/cert.pem]");
    process.exit(2);
}

var privPath = process.argv[2];
var certPath = process.argv[3];
var domain = process.argv[4];

https.createServer({
	key: fs.readFileSync(privPath),
	cert: fs.readFileSync(certPath)
}, app).listen(443);

app.get('/', function (req, res) {
	console.log("Received HTTPS request!");
	res.header('Content-type', 'text/html');
	return res.end("<h1>You have successfully configured HTTPS for " + domain + "</h1>");
});

// Redirect from http port 80 to https
var http = require('http');
http.createServer(function (req, res) {
    console.log("HTTP request: redirect to HTTPS!");
    res.writeHead(301,
        {"Location": "https://" + req.headers['host'] + req.url}
    );
    res.end();
}).listen(80);

console.log("Test server started!");
console.log("Please check that " + domain + " works as expected before continuing!");
console.log("Press any key to kill test server and continue the process ...");

process.stdin.setRawMode(true);
process.stdin.resume();
process.stdin.on('data', process.exit.bind(process, 0));

