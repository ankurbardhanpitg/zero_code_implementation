const express = require("express");
const houseRoutes = require("./modules/house/house.routes");

const app = express();
const PORT = process.env.PORT || 3002;

app.use(express.json());

app.get("/", (_req, res) => {
  res.json({
    message: "House API is running",
    endpoints: {
      addHouse: "POST /houses",
      fetchHouses: "GET /houses",
      fetchHouseById: "GET /houses/:id",
      deleteHouse: "DELETE /houses/:id",
    },
  });
});

app.use("/houses", houseRoutes);

app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
