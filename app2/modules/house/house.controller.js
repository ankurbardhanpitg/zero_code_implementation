const houseStore = require("./house.store");

async function addHouse(req, res) {
  const { address, city, price } = req.body || {};

  if (!address || !city || price === undefined) {
    return res.status(400).json({
      error: "address, city, and price are required",
    });
  }

  const house = await houseStore.create({ address, city, price });
  return res.status(201).json(house);
}

async function fetchHouses(_req, res) {
  const houses = await houseStore.getAll();
  return res.json(houses);
}

async function fetchHouseById(req, res) {
  const house = await houseStore.getById(req.params.id);

  if (!house) {
    return res.status(404).json({ error: "house not found" });
  }

  return res.json(house);
}

async function deleteHouse(req, res) {
  const deletedHouse = await houseStore.remove(req.params.id);

  if (!deletedHouse) {
    return res.status(404).json({ error: "house not found" });
  }

  return res.json({
    message: "house deleted",
    house: deletedHouse,
  });
}

module.exports = {
  addHouse,
  fetchHouses,
  fetchHouseById,
  deleteHouse,
};
