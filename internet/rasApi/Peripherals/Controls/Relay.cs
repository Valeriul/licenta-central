

using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using RasberryAPI.Peripherals;
using System.Text;
using RasberryAPI.Services;

namespace RasberryAPI.Peripherals
{
    public class Relay : Control
    {
        private static readonly Random random = new Random();
        public string State { get; set; }

        public Relay(string uuid, string url) : base(uuid, url)
        {
            BatteryLevel = random.Next(0, 100);
        }


        public override string GetData()
        {
            var endpoint = "http://" + Url + "/module/state?uuid=" + UUId;

            using HttpClient client = new HttpClient();
            var response = client.GetAsync(endpoint).Result;
            var responseData = response.Content.ReadAsStringAsync().Result;


            try{
                string sanitizedResponse = JsonConvert.DeserializeObject<string>(responseData) ?? string.Empty;
                var responseObject = JsonConvert.DeserializeObject<Dictionary<string, object>>(sanitizedResponse);
                State = responseObject["isOn"].ToString();
            }
            catch (Exception e)
            {
                return null;
            }

            string insertQuery = "INSERT INTO relay_state_data (uuid, state) VALUES (@uuid, @state);";
            var parameters = new Dictionary<string, object>
            {
                { "uuid", UUId },
                { "state", State == "False" ? 1 : 0 }
            };
            MySqlDatabaseService.Instance.ExecuteQueryAsync(insertQuery, parameters); 

            return responseData;
        }

        public override void SetState(string state)
        {
            var endpoint = $"http://{Url}/module/state?uuid={UUId}";

            using HttpClient client = new HttpClient();

            var stateDict = new Dictionary<string, string>
            {
                { "state", state }
            };
            var content = new StringContent(JsonConvert.SerializeObject(stateDict), Encoding.UTF8, "application/json");

            var response = client.PostAsync(endpoint, content).Result;

            State = response.Content.ReadAsStringAsync().Result;

        }


        public override void HandleRequest(string request)
        {
            var ledRequest = Newtonsoft.Json.JsonConvert.DeserializeObject<RelayRequest>(request);
            switch (ledRequest.type)
            {
                case "SET_ON":
                    SetState("HIGH");
                    break;
                case "SET_OFF":
                    SetState("LOW");
                    break;
                default:
                    Console.WriteLine("Unknown request type.");
                    break;
            }
        }
    }

    public class RelayRequest
    {
        public string type { get; set; }
        public string value { get; set; }
    }
}
