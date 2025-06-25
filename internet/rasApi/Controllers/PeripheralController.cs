using Microsoft.AspNetCore.Mvc;
using RasberryAPI.Peripherals;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace BackendAPI.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class PeripheralController : ControllerBase
    {

        [HttpGet("list")]
        public IActionResult ListPeripherals()
        {
            try
            {
                var peripherals = PeripheralManager.Instance.GetAllPeripherals();
                return Ok(peripherals);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error listing peripherals: {ex.Message}");
                return StatusCode(500, "An error occurred while listing peripherals.");
            }
        }
        
        [HttpPost("refreshPeripherals")]
        public async Task<IActionResult> RefreshPeripherals([FromBody] List<PeripheralConfig> peripherals)
        {
            try
            {
                await PeripheralManager.Instance.RefreshPeripherals(peripherals);
                return Ok("Peripherals refreshed successfully.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error refreshing peripherals: {ex.Message}");
                return StatusCode(500, "An error occurred while refreshing peripherals.");
            }
        }



        [HttpDelete("remove")]
        public IActionResult RemovePeripheral([FromQuery] string uuid)
        {
            if (string.IsNullOrEmpty(uuid))
            {
                return BadRequest("UUID is required.");
            }

            try
            {
                PeripheralManager.Instance.RemovePeripheral(uuid);
                return Ok("Peripheral removed successfully.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error removing peripheral: {ex.Message}");
                return StatusCode(500, "An error occurred while removing the peripheral.");
            }
        }

        [HttpDelete("removeAll")]

        public IActionResult RemoveAllPeripherals()
        {
            try
            {
                PeripheralManager.Instance.RemoveAllPeripherals();
                return Ok("All peripherals removed successfully.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error removing all peripherals: {ex.Message}");
                return StatusCode(500, "An error occurred while removing all peripherals.");
            }
        }
    }
}
