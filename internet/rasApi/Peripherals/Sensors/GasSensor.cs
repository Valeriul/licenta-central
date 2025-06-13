

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using RasberryAPI.Peripherals;
using Newtonsoft.Json;

namespace RasberryAPI.Peripherals
{
    public class GasSensor : Sensor
    {
        private static readonly Random random = new Random();
        public string State { get; set; }

        public GasSensor(string uuid, string url) : base(uuid, url) {
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
                State = responseObject["gasValue"].ToString();
            }
            catch (Exception e)
            {
                return null;
            }


            return responseData;
        }
    }
}