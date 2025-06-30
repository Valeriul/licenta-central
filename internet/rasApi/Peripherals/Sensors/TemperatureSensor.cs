

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using RasberryAPI.Peripherals;
using Newtonsoft.Json;
using RasberryAPI.Services;

namespace RasberryAPI.Peripherals
{
    public class TemperatureSensor : Sensor
    {
        private static readonly Random random = new Random();
        public string State { get; set; }

        public TemperatureSensor(string uuid, string url) : base(uuid, url) {
            BatteryLevel = random.Next(0, 100);
        }

        public override string GetData()
        {
            var endpoint = "http://" + Url + "/module/state?uuid=" + UUId;

            using HttpClient client = new HttpClient();
            client.Timeout = TimeSpan.FromSeconds(2);
            
            try
            {
                var response = client.GetAsync(endpoint).Result;
                var responseData = response.Content.ReadAsStringAsync().Result;

                string sanitizedResponse = JsonConvert.DeserializeObject<string>(responseData) ?? string.Empty;
                var responseObject = JsonConvert.DeserializeObject<Dictionary<string, object>>(sanitizedResponse);
                State = responseObject["temperatureC"].ToString();

                string insertQuery = "INSERT INTO temperature_sensor_data (uuid, temperature) VALUES (@uuid, @temperature);";
                var parameters = new Dictionary<string, object>
                {
                    { "uuid", UUId },
                    { "temperature", State }
                };
                MySqlDatabaseService.Instance.ExecuteQueryAsync(insertQuery, parameters);

                return responseData;
            }
            catch (Exception e)
            {
                return string.Empty;
            }
        }
    }
}