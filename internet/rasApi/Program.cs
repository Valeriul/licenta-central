using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Configuration;
using RasberryAPI.Services;
using RasberryAPI.Middlewares;
using RasberryAPI.Peripherals;

namespace RasberryAPI
{
    public class Program
    {
        public static void Main(string[] args)
        {
            var builder = WebApplication.CreateBuilder(args);

            // Configure services
            builder.Services.AddControllers();
            builder.Services.AddEndpointsApiExplorer();
            builder.Services.AddSwaggerGen();

            // Build the app
            var app = builder.Build();

            // Configure the HTTP request pipeline
            app.UsePathBase("/rasberry");
            app.UseDeveloperExceptionPage();

            app.UseSwagger();
            app.UseSwaggerUI(c =>
            {
                c.SwaggerEndpoint("/rasberry/swagger/v1/swagger.json", "WebSocket Server API v1");
                c.RoutePrefix = string.Empty; 
            });

            // Initialize services
            PeripheralManager.Instance.InitializeFromJson();
            MySqlDatabaseService.Initialize(app.Configuration);

            // Configure middleware
            app.UseWebSockets();
            app.UseMiddleware<WebSocketMiddleware>();

            app.UseRouting();
            app.MapControllers();

            app.Run();
        }
    }
}