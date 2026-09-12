const fs = require("fs/promises");
const path = require("path");

const DB_PATH = path.join(__dirname, "../../data/houses.json");

async function readHouses() {
  try {
    const data = await fs.readFile(DB_PATH, "utf8");
    return JSON.parse(data);
  } catch (error) {
    if (error.code === "ENOENT") {
      await writeHouses([]);
      return [];
    }
    throw error;
  }
}

async function writeHouses(houses) {
  await fs.writeFile(DB_PATH, JSON.stringify(houses, null, 2), "utf8");
}

async function getAll() {
  return readHouses();
}

function nextId(houses) {
  return houses.reduce((max, house) => Math.max(max, Number(house.id) || 0), 0) + 1;
}

function matchesId(house, id) {
  return Number(house.id) === Number(id);
}

async function getById(id) {
  const houses = await readHouses();
  return houses.find((house) => matchesId(house, id)) || null;
}

async function create(houseData) {
  const houses = await readHouses();
  const house = {
    id: nextId(houses),
    address: houseData.address,
    city: houseData.city,
    price: Number(houseData.price),
    createdAt: new Date().toISOString(),
  };

  houses.push(house);
  await writeHouses(houses);
  return house;
}

async function remove(id) {
  const houses = await readHouses();
  const index = houses.findIndex((house) => matchesId(house, id));

  if (index === -1) {
    return null;
  }

  const [deletedHouse] = houses.splice(index, 1);
  await writeHouses(houses);
  return deletedHouse;
}

module.exports = {
  getAll,
  getById,
  create,
  remove,
};
