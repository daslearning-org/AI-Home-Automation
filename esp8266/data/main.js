let controlUrl = `http://${window.location.hostname}/led/control`;
let getUrl = `http://${window.location.hostname}/led/stat`;

let led1Stat = "unknown";
let led2Stat = "unknown";

function getStat() {
  var xhr = new XMLHttpRequest();
  xhr.open("GET", getUrl, true);
  xhr.getResponseHeader("Content-type", "application/json");
  xhr.send();
  xhr.onload = function() {
    var data = JSON.parse(xhr.responseText);
    led1Stat = data.led1;
    led2Stat = data.led2;
    if(led1Stat === "on"){
      document.getElementById("led1Stat").textContent = "LED1 Status: ON";
      document.getElementById("ledOne").textContent = "OFF LED1";
      document.getElementById("ledOne").classList.remove("button-on");
      document.getElementById("ledOne").classList.add("button-off");
    }
    else if(led1Stat === "off"){
      document.getElementById("led1Stat").textContent = "LED1 Status: OFF";
      document.getElementById("ledOne").textContent = "ON LED1";
      document.getElementById("ledOne").classList.remove("button-off");
      document.getElementById("ledOne").classList.add("button-on");
    }

    if(led2Stat === "on"){
      document.getElementById("led2Stat").textContent = "LED2 Status: ON";
      document.getElementById("ledTwo").textContent = "OFF LED2";
      document.getElementById("ledTwo").classList.remove("button-on");
      document.getElementById("ledTwo").classList.add("button-off");
    }
    else if(led2Stat === "off"){
      document.getElementById("led2Stat").textContent = "LED2 Status: OFF";
      document.getElementById("ledTwo").textContent = "ON LED2";
      document.getElementById("ledTwo").classList.remove("button-off");
      document.getElementById("ledTwo").classList.add("button-on");
    }
  };
}

function changeStat(selectLed) {
  let ledNum;
  let ledOn;
  if (selectLed === "ledOne"){
    if(led1Stat === "on"){
      ledNum = 1;
      ledOn = false;
    }
    else if(led1Stat === "off"){
      ledNum = 1;
      ledOn = true;
    }
  }
  if (selectLed === "ledTwo"){
    if(led2Stat === "on"){
      ledNum = 2;
      ledOn = false;
    }
    else if(led2Stat === "off"){
      ledNum = 2;
      ledOn = true;
    }
  }

  let jsonBody = {
    ledNum: ledNum,
    ledOn: ledOn
  }

  const xhr = new XMLHttpRequest();
  xhr.open('POST', controlUrl, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.setRequestHeader('Cache-Control', 'no-cache');
  xhr.onload = function() {
    if (xhr.status === 200) {
      const response = JSON.parse(xhr.responseText);
      alert(`API Message: ${response.message}`);
    }
    else {
      console.error('Error:', xhr.status, xhr.statusText);
      alert("Some problem occurred in the API, please try again");
    }
  };
  xhr.send(JSON.stringify(jsonBody));

}

document.getElementById("ledOne").addEventListener("click", function(event) {
  changeStat("ledOne");
  getStat();
});

document.getElementById("ledTwo").addEventListener("click", function(event) {
  changeStat("ledTwo");
  getStat();
});
