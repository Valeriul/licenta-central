using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography.X509Certificates;
using Newtonsoft.Json;
using RasberryAPI.Middlewares;
using RasberryAPI.Services;

namespace RasberryAPI.Peripherals
{
    public class PeripheralFactory
    {
        public IPeripheral? CreatePeripheral(PeripheralConfig config)
        {
            return config.PeripheralType.ToLower() switch
            {
                "led" => new LedControl(config.Uuid, config.Url),
                "gassensor" => new GasSensor(config.Uuid, config.Url),
                "temperaturesensor" => new TemperatureSensor(config.Uuid, config.Url),
                "relay" => new Relay(config.Uuid, config.Url),
                _ => null
            };
        }
    }

    public sealed class PeripheralManager
    {

        private static readonly Lazy<PeripheralManager> _instance = new Lazy<PeripheralManager>(() => new PeripheralManager());
        public static PeripheralManager Instance => _instance.Value;

        private readonly List<IPeripheral> _peripherals;
        private readonly PeripheralFactory _peripheralFactory;

        private readonly string filePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Peripherals", "peripherals.json");


        private PeripheralManager()
        {
            _peripherals = new List<IPeripheral>();
            _peripheralFactory = new PeripheralFactory();
        }


        public void InitializeFromJson()
        {
            try
            {
                if (!File.Exists(filePath))
                {
                    Console.WriteLine($"File not found: {filePath}");
                    return;
                }

                var jsonContent = File.ReadAllText(filePath);
                var peripheralConfigs = JsonConvert.DeserializeObject<List<PeripheralConfig>>(jsonContent);

                foreach (var config in peripheralConfigs)
                {
                    var peripheral = _peripheralFactory.CreatePeripheral(config);
                    if (peripheral != null)
                    {
                        _peripherals.Add(peripheral);
                        Console.WriteLine($"Initialized peripheral: {config.PeripheralType} with UUID {config.Uuid}");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error initializing peripherals: {ex.Message}");
            }
        }

        public void AddPeripheral(PeripheralConfig config)
        {
            var peripheral = _peripheralFactory.CreatePeripheral(config);
            if (peripheral != null)
            {
                _peripherals.Add(peripheral);

                var peripheralConfigs = new List<PeripheralConfig>();
                if (File.Exists(filePath))
                {
                    var jsonContent = File.ReadAllText(filePath);
                    peripheralConfigs = JsonConvert.DeserializeObject<List<PeripheralConfig>>(jsonContent);
                }

                peripheralConfigs.Add(config);

                File.WriteAllText(filePath, JsonConvert.SerializeObject(peripheralConfigs, Formatting.Indented));

                Console.WriteLine($"Added peripheral: {config.PeripheralType} with UUID {config.Uuid}");

                NotifyPeripheralAdded(peripheral);
            }
        }

        public void RemovePeripheral(string uuid)
        {
            var peripheral = _peripherals.FirstOrDefault(p => p.UUId == uuid);
            if (peripheral != null)
            {
                _peripherals.Remove(peripheral);

                var peripheralConfigs = new List<PeripheralConfig>();
                if (File.Exists(filePath))
                {
                    var jsonContent = File.ReadAllText(filePath);
                    peripheralConfigs = JsonConvert.DeserializeObject<List<PeripheralConfig>>(jsonContent);
                }

                peripheralConfigs.RemoveAll(p => p.Uuid == uuid);

                File.WriteAllText(filePath, JsonConvert.SerializeObject(peripheralConfigs, Formatting.Indented));

                Console.WriteLine($"Removed peripheral with UUID {uuid}");

                NotifyPeripheralRemoved(uuid);
            }
        }

        public async void NotifyPeripheralAdded(IPeripheral addedPeripheral)
        {

            var message = new
            {
                type = "peripheralAdded",
                data = new
                {
                    uuid = addedPeripheral.UUId,
                    type = addedPeripheral.GetType().Name
                }
            };

            if (WebSocketMiddleware.IsConnected())
            {
                var messageJson = JsonConvert.SerializeObject(message);
                await WebSocketMiddleware.SendMessageAsync(messageJson);
            }
        }

        public async void NotifyPeripheralRemoved(string uuid)
        {

            var message = new
            {
                type = "peripheralRemoved",
                data = new
                {
                    uuid = uuid
                }
            };

            if (WebSocketMiddleware.IsConnected())
            {
                var messageJson = JsonConvert.SerializeObject(message);
                await WebSocketMiddleware.SendMessageAsync(messageJson);
            }
        }


        public async Task<string> HandleRequest(string uuid, string requestData)
        {
            var peripheral = _peripherals.FirstOrDefault(p => p.UUId == uuid);
            if (peripheral != null)
            {
                peripheral.HandleRequest(requestData);
                return peripheral.GetData();
            }

            return string.Empty;
        }

        public async Task RefreshPeripherals(List<PeripheralConfig> peripherals)
        {
            try
            {
                var uuids = peripherals.Select(p => p.Uuid).ToList();
                var existingUuids = _peripherals.Select(p => p.UUId).ToList();

                foreach (var config in peripherals)
                {
                    if (existingUuids.Contains(config.Uuid))
                    {
                       await Task.Run(() => RemovePeripheral(config.Uuid));
                    }
                    await Task.Run(() => AddPeripheral(config));
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error refreshing peripherals: {ex.Message}");
            }
        }

        public IEnumerable<string> GetAllPeripherals()
        {
            if (_peripherals.Count == 0)
            {
                return null;
            }

            var jsonO = _peripherals.Select(p => new
            {
                uuid = p.UUId,
                type = p.GetType().Name
            });

            return new List<string> { JsonConvert.SerializeObject(jsonO) };
        }

        public IEnumerable<string> GetAllData()
        {
            var jsonO = new List<object>();
            foreach (var peripheral in _peripherals)
            {
                object peripheralData;
                try
                {
                    peripheralData = peripheral.GetData();
                }
                catch (Exception)
                {
                    continue; // Skip this peripheral if an error occurs
                }
                jsonO.Add(new
                {
                    uuid = peripheral.UUId,
                    data = peripheralData
                });
            }

            return new List<string> { JsonConvert.SerializeObject(jsonO) };
        }

        public async Task<string> GetAggregatedData(string uuid, string requestData)
        {
            try
            {
                var request = JsonConvert.DeserializeObject<Dictionary<string, string>>(requestData);
                
                // Check if required keys exist
                if (!request.ContainsKey("date_start") || !request.ContainsKey("date_end") || !request.ContainsKey("type"))
                {
                    return JsonConvert.SerializeObject(new { error = "Missing required parameters: date_start, date_end, or type" });
                }

                var date_start = request["date_start"];
                var date_end = request["date_end"];
                var type = request["type"];

                DateTime startDate, endDate;
                TimeSpan timeDifference;
                
                try
                {
                    startDate =  DateTime.Parse(date_start);
                    endDate =  DateTime.Parse(date_end);
                    timeDifference = endDate - startDate;
                }
                catch (Exception)
                {
                    return JsonConvert.SerializeObject(new { error = "Invalid date format. Use format: yyyy-MM-dd HH:mm:ss" });
                }

                // Check for negative time difference
                if (timeDifference.TotalMilliseconds < 0)
                {
                    return JsonConvert.SerializeObject(new { error = "End date must be after start date" });
                }

                string aggregationLevel;
                if (timeDifference.TotalHours < 3)
                    aggregationLevel = "minute";
                else if (timeDifference.TotalDays < 3)
                    aggregationLevel = "hourly";
                else
                    aggregationLevel = "daily";

                string tableName = type switch
                {
                    "LedControl" => "led_brightness_data",
                    "GasSensor" => "gas_sensor_data",
                    "TemperatureSensor" => "temperature_sensor_data",
                    "Relay" => "relay_state_data",
                    _ => null
                };

                if (tableName == null)
                {
                    return JsonConvert.SerializeObject(new { error = $"Invalid type: {type}. Valid types: LedControl, GasSensor, TemperatureSensor, Relay" });
                }

                var query = $"SELECT * FROM {tableName} WHERE uuid = @uuid AND timestamp >= @startDate AND timestamp <= @endDate AND aggregation_level = @aggregationLevel ORDER BY timestamp";
                var parameters = new Dictionary<string, object>
                {
                    { "@uuid", uuid },
                    { "@startDate", startDate.ToString("yyyy-MM-dd HH:mm:ss") },
                    { "@endDate", endDate.ToString("yyyy-MM-dd HH:mm:ss") },
                    { "@aggregationLevel", aggregationLevel }
                };

                var data = await MySqlDatabaseService.Instance.ExecuteQueryAsync(query, parameters);

                if (data.Count == 0)
                {
                    return JsonConvert.SerializeObject(new { 
                        message = $"No data found for UUID {uuid} between {date_start} and {date_end} at {aggregationLevel} level",
                        data = new object[0]
                    });
                }

                data.ForEach(d => d.Remove("aggregation_level"));
                data.ForEach(d => d.Remove("uuid"));
                data.ForEach(d => d.Remove("id"));
                data.ForEach(d => d.Remove("aggregated"));
                return JsonConvert.SerializeObject(data);
            }
            catch (JsonException)
            {
                return JsonConvert.SerializeObject(new { error = "Invalid JSON format in request data" });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error in GetAggregatedData: {ex.Message}");
                return JsonConvert.SerializeObject(new { error = ex.Message });
            }
        }

        public IEnumerable<string> GetAllSensorData()
        {

            var jsonO = _peripherals.Where(p => p is Sensor).Select(p => new
            {
                uuid = p.UUId,
                data = p.GetData()
            });

            return new List<string> { JsonConvert.SerializeObject(jsonO) };
        }



        public void RemoveAllPeripherals()
        {
            for (int i = _peripherals.Count - 1; i >= 0; i--)
            {
                RemovePeripheral(_peripherals[i].UUId);
            }
            File.WriteAllText(filePath, "[]");
        }
    }

    public class PeripheralConfig
    {
        public string PeripheralType { get; set; }
        public string Uuid { get; set; }
        public string Url { get; set; }
    }
}
